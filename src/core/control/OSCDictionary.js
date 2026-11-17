/**
 * OSCDictionary.js — Dizionario completo OSC compatibile con QLab 5 & ShowSuite
 * 
 * Implementa le specifiche del protocollo OSC di QLab 5:
 * - Controlli globali di trasporto del Workspace (/go, /stop, /panic, /pause, /resume, /reset, /load, /next, /previous)
 * - Controlli specifici per Cue identificata per numero (/cue/{number}/start, /stop, /arm, /preWait, ecc.)
 * - Controlli per ID univoco (/cue_id/{id}/...)
 * - Controlli sulla Cue selezionata / in Standby (/cue/selected/...)
 * - Regolazione audio matrix crosspoint (/cue/{number}/level/{in}/{out}/decibel)
 * - Query di stato (/runningOrPausedCues, /standbyCue, /cue/{number}/name)
 * - Integrazione estesa con Lightkey LiveController (/live/grandMaster, /live/blackout, /live/cell/trigger, ecc.)
 */

export class OSCDictionary {
  constructor(options = {}) {
    this.customRoutes = new Map();
  }

  /**
   * Registra una route OSC personalizzata
   * @param {string|RegExp} pattern Indirizzo esatto o regex
   * @param {Function} handler Funzione (params, args, context) => result
   */
  registerRoute(pattern, handler) {
    this.customRoutes.set(pattern, handler);
  }

  /**
   * Esegue il dispatching di un comando OSC verso i motori di ShowSuite
   * 
   * @param {string} address Indirizzo OSC (es. "/cue/1/start")
   * @param {Array<any>} args Argomenti associati (es. [10.5])
   * @param {Object} context Contesto con cueScheduler, liveController, cueEngine, ecc.
   * @returns {{ handled: boolean, replyAddress?: string, replyArgs?: Array<any>, data?: any, error?: string }}
   */
  dispatch(address, args = [], context = {}) {
    if (!address || typeof address !== 'string') {
      return { handled: false, error: 'Indirizzo OSC nullo o non valido' };
    }

    const { cueScheduler, liveController, cueEngine } = context;

    // Normalizza l'indirizzo
    const cleanAddress = address.trim().replace(/\/+$/, '') || '/';

    // ─── 1. Custom Routes registrate dall'utente ────────────────────
    for (const [pattern, handler] of this.customRoutes.entries()) {
      if (typeof pattern === 'string' && pattern === cleanAddress) {
        const res = handler({}, args, context);
        return { handled: true, data: res };
      } else if (pattern instanceof RegExp) {
        const match = cleanAddress.match(pattern);
        if (match) {
          const res = handler(match.groups || match, args, context);
          return { handled: true, data: res };
        }
      }
    }

    // ─── 2. Workspace Global Transport (QLab 5) ─────────────────────
    switch (cleanAddress) {
      case '/go': {
        const success = cueScheduler ? cueScheduler.go() : false;
        return { handled: true, replyAddress: '/reply/go', replyArgs: [success ? 'ok' : 'failed'], data: success };
      }

      case '/stop': {
        const success = cueScheduler ? cueScheduler.stop() : false;
        return { handled: true, replyAddress: '/reply/stop', replyArgs: ['ok'], data: success };
      }

      case '/hardStop': {
        if (cueScheduler) cueScheduler.hardStop();
        return { handled: true, replyAddress: '/reply/hardStop', replyArgs: ['ok'] };
      }

      case '/pause': {
        const success = cueScheduler ? cueScheduler.pause() : false;
        return { handled: true, replyAddress: '/reply/pause', replyArgs: [success ? 'ok' : 'none_paused'], data: success };
      }

      case '/resume': {
        const success = cueScheduler ? cueScheduler.resume() : false;
        return { handled: true, replyAddress: '/reply/resume', replyArgs: [success ? 'ok' : 'none_resumed'], data: success };
      }

      case '/panic': {
        const fadeTime = args.length > 0 && typeof args[0] === 'number' ? args[0] : 1.0;
        if (cueScheduler) cueScheduler.panic(fadeTime);
        return { handled: true, replyAddress: '/reply/panic', replyArgs: ['ok', fadeTime] };
      }

      case '/reset': {
        if (cueScheduler) {
          cueScheduler.stop();
          cueScheduler.setStandbyIndex(0);
        }
        return { handled: true, replyAddress: '/reply/reset', replyArgs: ['ok'] };
      }

      case '/load': {
        const cue = cueScheduler ? cueScheduler.getStandbyCue() : null;
        const loaded = cue ? cue.load() : false;
        return { handled: true, replyAddress: '/reply/load', replyArgs: [loaded ? 'ok' : 'failed'], data: loaded };
      }

      case '/next':
      case '/playhead/next': {
        if (cueScheduler) cueScheduler.advancePlayhead();
        const cur = cueScheduler ? cueScheduler.getStandbyCue() : null;
        return { handled: true, replyAddress: '/reply/next', replyArgs: [cur ? cur.number : 'none'], data: cur };
      }

      case '/previous':
      case '/playhead/previous': {
        if (cueScheduler) cueScheduler.previousPlayhead();
        const cur = cueScheduler ? cueScheduler.getStandbyCue() : null;
        return { handled: true, replyAddress: '/reply/previous', replyArgs: [cur ? cur.number : 'none'], data: cur };
      }

      case '/runningCues':
      case '/runningOrPausedCues': {
        const list = cueScheduler && cueScheduler.runningCues ? Array.from(cueScheduler.runningCues).map(c => ({
          id: c.id,
          number: c.number,
          name: c.name,
          state: c.state,
          phase: c.currentPhase,
        })) : [];
        return {
          handled: true,
          replyAddress: '/reply/runningOrPausedCues',
          replyArgs: [JSON.stringify(list)],
          data: list,
        };
      }

      case '/standbyCue': {
        const cue = cueScheduler ? cueScheduler.getStandbyCue() : null;
        const info = cue ? { id: cue.id, number: cue.number, name: cue.name, type: cue.type, armed: cue.armed } : null;
        return {
          handled: true,
          replyAddress: '/reply/standbyCue',
          replyArgs: [JSON.stringify(info)],
          data: info,
        };
      }
    }

    // ─── 3. Cue Targeting (/cue/{target}/... o /cue_id/{target}/...) ─
    const cueRegex = /^\/cue\/(?<target>[^\/]+)\/(?<action>.+)$/;
    const cueIdRegex = /^\/cue_id\/(?<target>[^\/]+)\/(?<action>.+)$/;

    let cueMatch = cleanAddress.match(cueRegex);
    let isIdLookup = false;

    if (!cueMatch) {
      cueMatch = cleanAddress.match(cueIdRegex);
      if (cueMatch) isIdLookup = true;
    }

    if (cueMatch) {
      const { target, action } = cueMatch.groups;
      let cue = null;

      if (!cueScheduler) {
        return { handled: false, error: 'CueScheduler non configurato nel contesto' };
      }

      if (target === 'selected' || target === 'standby') {
        cue = cueScheduler.getStandbyCue();
      } else if (isIdLookup) {
        cue = cueScheduler.findCueById(target);
      } else {
        cue = cueScheduler.findCueByNumber(target);
        if (!cue) {
          // Prova fallback per ID
          cue = cueScheduler.findCueById(target);
        }
      }

      if (!cue) {
        return {
          handled: true,
          error: `Cue "${target}" non trovata nel workspace`,
          replyAddress: `/reply/${isIdLookup ? 'cue_id' : 'cue'}/${target}/error`,
          replyArgs: ['not_found'],
        };
      }

      return this._handleCueAction(cue, action, args, cueScheduler, target);
    }

    // ─── 4. Lightkey Live Controller OSC Mappings ───────────────────
    if (cleanAddress.startsWith('/live/')) {
      return this._handleLightkeyAction(cleanAddress, args, context);
    }

    return { handled: false, error: `Comando OSC non riconosciuto: ${cleanAddress}` };
  }

  /**
   * Gestisce le azioni specifiche su una singola Cue
   */
  _handleCueAction(cue, action, args, cueScheduler, targetLabel) {
    const actionParts = action.split('/');
    const mainAction = actionParts[0];

    switch (mainAction) {
      case 'start':
      case 'go': {
        const success = cueScheduler.startCue(cue);
        return { handled: true, replyAddress: `/reply/cue/${targetLabel}/start`, replyArgs: [success ? 'ok' : 'failed'], data: success };
      }

      case 'stop': {
        const stopped = cue.stop();
        cueScheduler.runningCues.delete(cue);
        cueScheduler.emit('cueStopped', cue);
        return { handled: true, replyAddress: `/reply/cue/${targetLabel}/stop`, replyArgs: ['ok'], data: stopped };
      }

      case 'hardStop': {
        cue.stop();
        cueScheduler.runningCues.delete(cue);
        return { handled: true, replyAddress: `/reply/cue/${targetLabel}/hardStop`, replyArgs: ['ok'] };
      }

      case 'pause': {
        const paused = cue.pause();
        return { handled: true, replyAddress: `/reply/cue/${targetLabel}/pause`, replyArgs: [paused ? 'ok' : 'failed'], data: paused };
      }

      case 'resume': {
        const resumed = cue.resume();
        return { handled: true, replyAddress: `/reply/cue/${targetLabel}/resume`, replyArgs: [resumed ? 'ok' : 'failed'], data: resumed };
      }

      case 'load': {
        const loaded = cue.load();
        return { handled: true, replyAddress: `/reply/cue/${targetLabel}/load`, replyArgs: [loaded ? 'ok' : 'failed'], data: loaded };
      }

      case 'reset': {
        cue.reset();
        return { handled: true, replyAddress: `/reply/cue/${targetLabel}/reset`, replyArgs: ['ok'] };
      }

      case 'arm': {
        if (args.length > 0) {
          cue.armed = Boolean(args[0]);
        } else {
          cue.armed = !cue.armed;
        }
        return { handled: true, replyAddress: `/reply/cue/${targetLabel}/arm`, replyArgs: [cue.armed ? 1 : 0], data: cue.armed };
      }

      case 'disarm': {
        cue.armed = false;
        return { handled: true, replyAddress: `/reply/cue/${targetLabel}/disarm`, replyArgs: [0], data: false };
      }

      case 'flagged': {
        if (args.length > 0) {
          cue.flagged = Boolean(args[0]);
        } else {
          cue.flagged = !cue.flagged;
        }
        return { handled: true, replyAddress: `/reply/cue/${targetLabel}/flagged`, replyArgs: [cue.flagged ? 1 : 0], data: cue.flagged };
      }

      case 'unflagged': {
        cue.flagged = false;
        return { handled: true, replyAddress: `/reply/cue/${targetLabel}/unflagged`, replyArgs: [0], data: false };
      }

      case 'preWait': {
        if (args.length > 0) {
          cue.preWait = Math.max(0, Number(args[0]) || 0);
        }
        return { handled: true, replyAddress: `/reply/cue/${targetLabel}/preWait`, replyArgs: [cue.preWait], data: cue.preWait };
      }

      case 'duration': {
        if (args.length > 0) {
          cue.duration = Math.max(0, Number(args[0]) || 0);
        }
        return { handled: true, replyAddress: `/reply/cue/${targetLabel}/duration`, replyArgs: [cue.duration], data: cue.duration };
      }

      case 'postWait': {
        if (args.length > 0) {
          cue.postWait = Math.max(0, Number(args[0]) || 0);
        }
        return { handled: true, replyAddress: `/reply/cue/${targetLabel}/postWait`, replyArgs: [cue.postWait], data: cue.postWait };
      }

      case 'name': {
        if (args.length > 0) {
          cue.name = String(args[0]);
        }
        return { handled: true, replyAddress: `/reply/cue/${targetLabel}/name`, replyArgs: [cue.name], data: cue.name };
      }

      case 'notes': {
        if (args.length > 0) {
          cue.notes = String(args[0]);
        }
        return { handled: true, replyAddress: `/reply/cue/${targetLabel}/notes`, replyArgs: [cue.notes], data: cue.notes };
      }

      case 'number': {
        if (args.length > 0) {
          cue.number = String(args[0]);
        }
        return { handled: true, replyAddress: `/reply/cue/${targetLabel}/number`, replyArgs: [cue.number], data: cue.number };
      }

      case 'colorName': {
        if (args.length > 0) {
          cue.color = String(args[0]).toLowerCase();
        }
        return { handled: true, replyAddress: `/reply/cue/${targetLabel}/colorName`, replyArgs: [cue.color], data: cue.color };
      }

      case 'continueMode': {
        if (args.length > 0) {
          const modeVal = args[0];
          cue.continueMode = typeof modeVal === 'number' ? modeVal : String(modeVal);
        }
        return { handled: true, replyAddress: `/reply/cue/${targetLabel}/continueMode`, replyArgs: [cue.continueMode], data: cue.continueMode };
      }

      // Regolazione Audio Matrix: /cue/{target}/level/{inChannel}/{outChannel}/decibel
      case 'level': {
        if (actionParts.length >= 4 && actionParts[3] === 'decibel' && cue.audioMatrix) {
          const inCh = parseInt(actionParts[1], 10);
          const outCh = parseInt(actionParts[2], 10);
          if (args.length > 0) {
            const dbVal = Number(args[0]);
            cue.audioMatrix.setCrosspointLevel(inCh, outCh, dbVal);
            return {
              handled: true,
              replyAddress: `/reply/cue/${targetLabel}/level/${inCh}/${outCh}/decibel`,
              replyArgs: [dbVal],
              data: dbVal,
            };
          } else {
            const currentDb = cue.audioMatrix.getCrosspointLevel(inCh, outCh);
            return {
              handled: true,
              replyAddress: `/reply/cue/${targetLabel}/level/${inCh}/${outCh}/decibel`,
              replyArgs: [currentDb],
              data: currentDb,
            };
          }
        }
        break;
      }
    }

    return { handled: false, error: `Azione non supportata su Cue: "${action}"` };
  }

  /**
   * Gestisce comandi live per Lightkey LiveController
   */
  _handleLightkeyAction(address, args, context) {
    const { liveController, cueEngine } = context;

    switch (address) {
      case '/live/grandMaster': {
        if (!liveController) return { handled: false, error: 'LiveController assente' };
        if (args.length > 0) {
          let val = Number(args[0]);
          if (val > 1.0) val = val / 100.0; // Accetta sia 0..1 che 0..100%
          liveController.setGrandMaster(val);
        }
        return { handled: true, replyAddress: '/reply/live/grandMaster', replyArgs: [liveController.grandMaster] };
      }

      case '/live/speedMaster': {
        if (!liveController) return { handled: false, error: 'LiveController assente' };
        if (args.length > 0) {
          liveController.setSpeedMaster(Number(args[0]));
        }
        return { handled: true, replyAddress: '/reply/live/speedMaster', replyArgs: [liveController.speedMaster] };
      }

      case '/live/blackout': {
        if (!liveController) return { handled: false, error: 'LiveController assente' };
        const newState = args.length > 0 ? Boolean(args[0]) : !liveController.isBlackout;
        liveController.setBlackout(newState);
        return { handled: true, replyAddress: '/reply/live/blackout', replyArgs: [newState ? 1 : 0] };
      }

      case '/live/blind': {
        if (!liveController) return { handled: false, error: 'LiveController assente' };
        const newState = args.length > 0 ? Boolean(args[0]) : !liveController.isBlind;
        liveController.setBlind(newState);
        return { handled: true, replyAddress: '/reply/live/blind', replyArgs: [newState ? 1 : 0] };
      }

      case '/live/freeze': {
        if (!liveController) return { handled: false, error: 'LiveController assente' };
        const newState = args.length > 0 ? Boolean(args[0]) : !liveController.isFrozen;
        liveController.setFreeze(newState);
        return { handled: true, replyAddress: '/reply/live/freeze', replyArgs: [newState ? 1 : 0] };
      }

      case '/live/cue/go': {
        if (!cueEngine) return { handled: false, error: 'CueEngine assente' };
        cueEngine.go();
        return { handled: true, replyAddress: '/reply/live/cue/go', replyArgs: ['ok'] };
      }

      case '/live/cue/stop': {
        if (!cueEngine) return { handled: false, error: 'CueEngine assente' };
        cueEngine.stop();
        return { handled: true, replyAddress: '/reply/live/cue/stop', replyArgs: ['ok'] };
      }
    }

    // Trigger cella (/live/cell/{index}/trigger o /live/cell/{row}/{col}/trigger)
    const cellMatch = address.match(/^\/live\/cell\/(\d+)\/trigger$/);
    if (cellMatch && liveController) {
      const cellIdx = parseInt(cellMatch[1], 10);
      const res = liveController.triggerCell(cellIdx);
      return { handled: true, replyAddress: `/reply/live/cell/${cellIdx}/trigger`, replyArgs: ['ok'], data: res };
    }

    const cellRowColMatch = address.match(/^\/live\/cell\/(\d+)\/(\d+)\/trigger$/);
    if (cellRowColMatch && liveController) {
      const row = parseInt(cellRowColMatch[1], 10);
      const col = parseInt(cellRowColMatch[2], 10);
      const cellIdx = row * 8 + col;
      const res = liveController.triggerCell(cellIdx);
      return { handled: true, replyAddress: `/reply/live/cell/${row}/${col}/trigger`, replyArgs: ['ok'], data: res };
    }

    // Regolazione Group Fader (/live/group/{nameOrId}/level)
    const groupMatch = address.match(/^\/live\/group\/(?<groupId>[^\/]+)\/level$/);
    if (groupMatch && liveController) {
      const { groupId } = groupMatch.groups;
      const grp = liveController.groups.find(g => g.id === groupId || g.name.toLowerCase() === groupId.toLowerCase());
      const effectiveId = grp ? grp.id : groupId;
      if (args.length > 0) {
        let val = Number(args[0]);
        if (val > 1.0) val = val / 100.0;
        liveController.setGroupFader(effectiveId, val);
      }
      const lvl = grp ? grp.faderLevel : 0;
      return { handled: true, replyAddress: `/reply/live/group/${groupId}/level`, replyArgs: [lvl] };
    }

    return { handled: false, error: `Indirizzo /live sconosciuto: ${address}` };
  }
}
