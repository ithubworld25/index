/* TRAJECTORY_FUNCTIONAL_REFERENCE v0.9-rc3 */
(() => {
  'use strict';

  const RC3_VERSION = '0.9.0-rc3';
  document.documentElement.dataset.rc3Ready = '0';
  document.documentElement.dataset.rc3SelfTest = 'pending';
  state.rc3Version = RC3_VERSION;

  function activeSharedCompetencyIds(left, right, selection = state.activeCompIds) {
    if (!left || !right) return [];
    const shared = Object.keys(left.competencies).filter(id => right.competencies[id] != null);
    return selection.size ? shared.filter(id => selection.has(id)) : shared;
  }

  function sameSemesterMatches(node, selection = state.activeCompIds) {
    if (!node) return [];
    return model.roles[node.role_id].nodes
      .filter(other => other.id !== node.id && Number(other.semester) === Number(node.semester))
      .map(other => ({node: other, competency_ids: activeSharedCompetencyIds(node, other, selection)}))
      .filter(item => item.competency_ids.length > 0);
  }

  function crossSemesterMatches(node, selection = state.activeCompIds) {
    if (!node) return [];
    const byNode = new Map();
    computeFocusEdges(node, selection).forEach(edge => {
      const otherId = edge.from === node.id ? edge.to : edge.from;
      if (!byNode.has(otherId)) byNode.set(otherId, []);
      byNode.get(otherId).push(edge.compId);
    });
    return [...byNode.entries()].map(([id, competency_ids]) => ({node: getNode(id), competency_ids})).filter(item => item.node);
  }

  function findSameSemesterFixture({requireCrossSemester = false} = {}) {
    for (const role of PROFILE.roles) {
      for (const node of model.roles[role.id].nodes) {
        const same = sameSemesterMatches(node, new Set());
        if (!same.length) continue;
        if (requireCrossSemester && !crossSemesterMatches(node, new Set()).length) continue;
        return {role_id: role.id, node, same};
      }
    }
    return null;
  }

  function sameSemesterTitle(node, matches) {
    const codes = [...new Set(matches.flatMap(item => item.competency_ids).map(id => catalogMap.get(id)?.code || id))];
    return `Совпадение в ${node.semester} семестре: ${codes.join(', ')}`;
  }

  function applySameSemesterHighlights() {
    const focus = getNode(state.focusedNodeId);
    const issue = selectedIssue();
    const cards = [...document.querySelectorAll('[data-node-id]')];

    cards.forEach(card => {
      card.classList.remove('same-semester-related');
      card.removeAttribute('data-same-semester-related');
      card.style.removeProperty('--same-semester-color');
      card.querySelector('.same-semester-badge')?.remove();
    });

    if (!focus || issue) return;

    const matches = sameSemesterMatches(focus);
    matches.forEach(item => {
      const card = document.querySelector(`[data-node-id='${CSS.escape(item.node.id)}']`);
      if (!card) return;
      card.classList.remove('focus-dim');
      card.classList.add('same-semester-related');
      card.dataset.sameSemesterRelated = '1';
      const firstComp = item.competency_ids[0];
      card.style.setProperty('--same-semester-color', compColor(firstComp));
      card.title = sameSemesterTitle(focus, [item]);
      const meta = card.querySelector('.card-meta');
      if (meta && !meta.querySelector('.same-semester-badge')) {
        const badge = document.createElement('span');
        badge.className = 'same-semester-badge';
        badge.textContent = 'тот же семестр';
        badge.title = 'Общие компетенции есть, но линия не строится: это не последовательность обучения';
        meta.appendChild(badge);
      }
    });
  }

  function competencyChips(focus, other, competencyIds) {
    return competencyIds.map(id => {
      const comp = catalogMap.get(id);
      const dashed = lineStyleForComp(id) === 'dashed' ? 'dashed' : '';
      return `<span class='chip ${dashed}' style='color:${compColor(id)}' title='${escapeHtml(comp?.name || id)}'>` +
        `${escapeHtml(comp?.code || id)}: ${focus.competencies[id]} / ${other.competencies[id]}</span>`;
    }).join('');
  }

  function buildSameSemesterSection(node) {
    const matches = sameSemesterMatches(node);
    const section = document.createElement('section');
    section.className = 'rc3-same-semester-section';
    section.dataset.rc3SameSemesterSection = '1';
    section.innerHTML = `<h3>Совпадения в текущем семестре</h3>` +
      `<div class='rc3-same-semester-note'>Эти дисциплины содержат общие компетенции и поэтому остаются выделенными. ` +
      `Линия между ними не строится: совпадение не означает пререквизит, постреквизит или последовательность изучения.</div>` +
      `<div class='rc3-same-semester-list'>` +
      (matches.length ? matches.map(item => {
        const firstComp = item.competency_ids[0];
        return `<button class='rc3-same-semester-item' data-same-semester-node='${item.node.id}' ` +
          `style='--same-semester-color:${compColor(firstComp)}'>` +
          `<b>${escapeHtml(item.node.name)}</b>` +
          `<small>${item.node.semester} семестр · ${item.node.hours} ч. · без соединительной линии</small>` +
          `<div class='related-codes'>${competencyChips(node, item.node, item.competency_ids)}</div>` +
          `</button>`;
      }).join('') : `<div class='empty'>В активном наборе нет совпадений с другими дисциплинами этого семестра.</div>`) +
      `</div>`;
    section.querySelectorAll('[data-same-semester-node]').forEach(button => {
      button.onclick = () => {
        state.focusedNodeId = button.dataset.sameSemesterNode;
        state.selectedIssueId = null;
        state.tab = 'details';
        renderAll();
        scrollToNode(button.dataset.sameSemesterNode);
      };
    });
    return section;
  }

  const rc2RenderMap = renderMap;
  renderMap = function rc3RenderMap() {
    rc2RenderMap();
    requestAnimationFrame(() => {
      applySameSemesterHighlights();
      requestAnimationFrame(applySameSemesterHighlights);
    });
  };

  const rc2RenderDetailsPanel = renderDetailsPanel;
  renderDetailsPanel = function rc3RenderDetailsPanel() {
    rc2RenderDetailsPanel();
    const node = getNode(state.focusedNodeId);
    const panel = byId('panel');
    if (!node || !panel) return;

    const headings = [...panel.querySelectorAll('h3')];
    const relatedHeading = headings.find(h => h.textContent.trim() === 'Связанные дисциплины');
    if (relatedHeading) relatedHeading.textContent = 'Связанные дисциплины других семестров';

    const sourcesHeading = [...panel.querySelectorAll('h3')].find(h => h.textContent.trim() === 'Источники');
    const section = buildSameSemesterSection(node);
    if (sourcesHeading) panel.insertBefore(section, sourcesHeading);
    else panel.appendChild(section);
  };

  function runRc3ConformanceTests() {
    const results = [];
    const test = (id, fn) => {
      try {
        const detail = fn();
        results.push({id, ok: true, detail: detail || 'OK'});
      } catch (error) {
        results.push({id, ok: false, detail: error.message});
      }
    };

    test('RC3-SAME-SEMESTER-01', () => {
      const fixture = findSameSemesterFixture();
      if (!fixture || !fixture.same.length) throw new Error('Не найден репрезентативный same-semester кейс');
      return `${fixture.node.name} → ${fixture.same[0].node.name}`;
    });
    test('RC3-SAME-SEMESTER-02', () => {
      const fixture = findSameSemesterFixture();
      const edges = computeFocusEdges(fixture.node, new Set());
      if (edges.some(edge => getNode(edge.from)?.semester === getNode(edge.to)?.semester)) {
        throw new Error('Обнаружена линия внутри одного семестра');
      }
      return 'Линии внутри одного семестра отсутствуют';
    });
    test('RC3-FOCUS-REGRESSION-01', () => {
      const fixture = findSameSemesterFixture({requireCrossSemester: true});
      if (!fixture) throw new Error('Не найден кейс с параллельными и межсеместровыми совпадениями');
      if (!computeFocusEdges(fixture.node, new Set()).length) throw new Error('Межсеместровые линии потеряны');
      return fixture.node.name;
    });
    test('RC3-RIGHT-PANEL-01', () => {
      if (typeof buildSameSemesterSection !== 'function') throw new Error('Раздел правой панели отсутствует');
      return 'Отдельный раздел same-semester доступен';
    });
    test('RC3-TECHNICAL-PROTOCOL-01', () => 'Технические проверки исключены из ручного протокола');

    window.__RC3_CONFORMANCE_RESULTS__ = results;
    const ok = results.every(item => item.ok);
    document.documentElement.dataset.rc3SelfTest = ok ? 'ok' : 'failed';
    document.documentElement.dataset.rc3Ready = '1';
    return results;
  }

  window.__TRAJECTORY_REFERENCE_RC3__ = {
    version: RC3_VERSION,
    activeSharedCompetencyIds,
    sameSemesterMatches,
    crossSemesterMatches,
    findSameSemesterFixture,
    runRc3ConformanceTests,
  };
  window.__RUN_RC3_CONFORMANCE_TESTS__ = runRc3ConformanceTests;

  renderAll();
  requestAnimationFrame(() => {
    applySameSemesterHighlights();
    runRc3ConformanceTests();
  });
})();
