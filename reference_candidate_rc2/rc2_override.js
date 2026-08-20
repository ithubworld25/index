/* TRAJECTORY_FUNCTIONAL_REFERENCE v0.9-rc2 */
(() => {
  'use strict';
  const RC2_VERSION = '0.9.0-rc2';
  const ISSUE_STATUS_SCHEMA = 'trajectory-issue-statuses-v1';
  const STATUS_STORAGE_KEY = `trajectory-issue-statuses::${PROFILE.id}::${PROFILE.academic_year}`;

  document.documentElement.dataset.rc2Ready = '0';
  document.documentElement.dataset.rc2SelfTest = 'pending';
  state.rc2Version = RC2_VERSION;
  state.viewedIssueIds = state.viewedIssueIds instanceof Set ? state.viewedIssueIds : new Set();

  STATUS_LABELS.fixed = 'Исправлена во внешнем источнике';
  STATUS_LABELS.normalized = 'Нормализована по решению';
  STATUS_LABELS.not_relevant = 'Не актуальна';

  function normalizeDisciplineName(value) {
    return String(value || '')
      .toLowerCase()
      .replace(/ё/g, 'е')
      .replace(/\u00a0/g, ' ')
      .replace(/[–—−]/g, '-')
      .replace(/\s*([\/.(),:-])\s*/g, '$1')
      .replace(/[.]+$/g, '')
      .replace(/\s+/g, ' ')
      .trim();
  }

  function sharedPeers(node) {
    if (!node) return [];
    const normalized = normalizeDisciplineName(node.name);
    return allNodes().filter(other =>
      normalizeDisciplineName(other.name) === normalized &&
      Number(other.semester) === Number(node.semester) &&
      Number(other.hours) === Number(node.hours)
    );
  }

  function sharedRoleIds(node) {
    return [...new Set(sharedPeers(node).map(peer => peer.role_id))];
  }

  function issueContextNodeIds(issue) {
    return new Set([
      ...(issue?.primary_node_ids || []),
      ...(issue?.existing_node_ids || []),
      ...(issue?.candidate_node_ids || []),
      ...(issue?.related_node_ids || []),
    ]);
  }

  function issueContextLabel(issue) {
    const primary = (issue.primary_node_ids || []).map(getNode).filter(Boolean);
    const roleSpecific = primary.find(node => node.role_id === state.roleId) || primary[0];
    if (roleSpecific) return roleSpecific.name;
    if (issue.semester_ids?.length) return 'Проблема семестра';
    return 'Общая проблема источника';
  }

  function issueRoleLabel(issue) {
    return (issue.role_ids || []).map(id => model.roles[id]?.label || id).join(' / ') || 'все БР';
  }

  function issueSemesterLabel(issue) {
    return issue.semester_ids?.length ? `${issue.semester_ids.join(', ')} семестр` : 'вне семестра';
  }

  function safeId(value) {
    return String(value).replace(/[^a-zA-Z0-9_-]+/g, '_');
  }

  function issueStatusPayload() {
    return {
      schema: ISSUE_STATUS_SCHEMA,
      functional_core_version: RC2_VERSION,
      program_profile_id: PROFILE.id,
      academic_year: PROFILE.academic_year,
      source_manifest_hash: sourceManifestHash,
      exported_at: new Date().toISOString(),
      statuses: Object.entries(state.issueStates).map(([issue_id, value]) => ({
        issue_id,
        status: value.status || 'open',
        comment: value.comment || '',
        changed_at: value.history?.length ? value.history[value.history.length - 1].at : null,
        history: deepClone(value.history || []),
      })),
    };
  }

  function issueStatusPayloadCompatible(payload) {
    return Boolean(
      payload &&
      payload.schema === ISSUE_STATUS_SCHEMA &&
      payload.program_profile_id === PROFILE.id &&
      payload.academic_year === PROFILE.academic_year &&
      payload.source_manifest_hash === sourceManifestHash &&
      Array.isArray(payload.statuses)
    );
  }

  function persistIssueStatuses() {
    try {
      localStorage.setItem(STATUS_STORAGE_KEY, JSON.stringify(issueStatusPayload()));
      const info = byId('sessionInfo');
      if (info) info.textContent = `Статусы: сохранены локально · ${new Date().toLocaleTimeString('ru-RU')}`;
    } catch (error) {
      const info = byId('sessionInfo');
      if (info) info.textContent = `Статусы: localStorage недоступен · ${error.message}`;
    }
  }

  function applyIssueStatusPayload(payload, {silent = false} = {}) {
    if (!issueStatusPayloadCompatible(payload)) {
      throw new Error('Файл статусов относится к другой специальности, версии или входному комплекту');
    }
    const knownIds = new Set(allIssues().map(issue => issue.issue_id));
    let applied = 0;
    let unknown = 0;
    payload.statuses.forEach(item => {
      if (!knownIds.has(item.issue_id)) {
        unknown += 1;
        return;
      }
      state.issueStates[item.issue_id] = {
        status: item.status || 'open',
        comment: item.comment || '',
        history: deepClone(item.history || []),
      };
      applied += 1;
    });
    persistIssueStatuses();
    if (!silent) toast(`Статусы загружены: ${applied}. Не найдено: ${unknown}.`);
    return {applied, unknown};
  }

  function restoreIssueStatuses() {
    try {
      const raw = localStorage.getItem(STATUS_STORAGE_KEY);
      if (!raw) return {applied: 0, unknown: 0};
      return applyIssueStatusPayload(JSON.parse(raw), {silent: true});
    } catch (error) {
      console.warn('RC2 status restore failed', error);
      return {applied: 0, unknown: 0};
    }
  }

  function downloadIssueStatuses() {
    downloadJson(`TRAJECTORY_ISSUE_STATUSES_${PROFILE.academic_year}_${Date.now()}.json`, issueStatusPayload());
  }

  function importIssueStatuses(file) {
    const reader = new FileReader();
    reader.onload = () => {
      try {
        applyIssueStatusPayload(JSON.parse(reader.result));
        renderAll();
      } catch (error) {
        toast(error.message);
      }
    };
    reader.readAsText(file);
  }

  function ensureZeroHourFixtures() {
    PROFILE.roles.forEach(role => {
      const createNode = () => ({
        id: `${role.id}::s2-zero-reference`,
        key: 's2-zero-reference',
        role_id: role.id,
        semester: 2,
        course: 1,
        name: 'Референс: самостоятельное изучение',
        code: 'REF.00',
        hours: 0,
        fgos_hours: 0,
        competencies: {},
        shared_key: 'shared-s2-zero-reference',
        canonical_id: 'reference-zero-hours',
        zero_hours: true,
        physical_education_exception: false,
        source_refs: {joint_plan: 'Тестовый профиль · 0 часов', matrix: 'Не применяется'},
      });
      if (!BASE_ROLES[role.id].nodes.some(node => node.key === 's2-zero-reference')) {
        BASE_ROLES[role.id].nodes.push(createNode());
      }
      if (!model.roles[role.id].nodes.some(node => node.key === 's2-zero-reference')) {
        model.roles[role.id].nodes.push(createNode());
      }
    });
  }

  function activeSemesterIssues(roleId, semester) {
    return allIssues().filter(issue =>
      issue.status === 'open' &&
      issue.role_ids?.includes(roleId) &&
      issue.semester_ids?.includes(semester) &&
      issueVisible(issue)
    );
  }

  function nodeParticipatesInIssue(node, issue) {
    if (issueContextNodeIds(issue).has(node.id)) return true;
    return Boolean(issue.semester_ids?.includes(node.semester) && issue.role_ids?.includes(node.role_id));
  }

  const originalVisibleNodes = visibleNodes;
  visibleNodes = function rc2VisibleNodes() {
    const role = roleObj();
    const q = state.search.trim().toLowerCase();
    const activeIssues = allIssues().filter(issue => issue.status === 'open' && issueVisible(issue));
    return role.nodes.filter(node => {
      if (!state.showZero && node.hours === 0) return false;
      if (q && !`${node.name} ${node.code}`.toLowerCase().includes(q)) return false;
      if (state.onlyIssues && !activeIssues.some(issue => nodeParticipatesInIssue(node, issue))) return false;
      return true;
    });
  };

  computeGlobalEdges = function rc2NoUnprovenGlobalEdges() {
    return [];
  };

  renderSelectionInfo = function rc2RenderSelectionInfo() {
    const info = byId('selectionInfo');
    if (!info) return;
    if (state.activeCompIds.size) {
      info.textContent = `Активно: ${state.activeCompIds.size}. Карточки с выбранными компетенциями выделены; линии появятся только после выбора дисциплины.`;
    } else {
      info.textContent = 'Фильтр не выбран. Клик по дисциплине покажет все её подтверждённые общие компетенции.';
    }
  };

  function addToolbarControls() {
    ['editBtn', 'saveSessionBtn', 'loadSessionBtn', 'snapshotBtn', 'changesBtn', 'undoBtn'].forEach(id => byId(id)?.classList.add('rc2-hidden'));
    state.editMode = false;

    const clearComps = byId('clearAllComps');
    if (clearComps) clearComps.textContent = 'Снять компетенции';

    if (clearComps && !byId('clearFocusBtn')) {
      const clearFocus = document.createElement('button');
      clearFocus.id = 'clearFocusBtn';
      clearFocus.className = 'mini';
      clearFocus.textContent = 'Снять фокус дисциплины';
      clearFocus.onclick = () => {
        state.focusedNodeId = null;
        state.selectedIssueId = null;
        state.tab = 'details';
        renderAll();
      };
      clearComps.parentElement.appendChild(clearFocus);

      const clearHighlight = document.createElement('button');
      clearHighlight.id = 'clearHighlightBtn';
      clearHighlight.className = 'mini';
      clearHighlight.textContent = 'Сбросить выделение';
      clearHighlight.onclick = () => {
        state.focusedNodeId = null;
        state.selectedIssueId = null;
        state.activeCompIds.clear();
        state.tab = 'details';
        renderAll();
      };
      clearComps.parentElement.appendChild(clearHighlight);
    }

    const issueControls = byId('showTechnical')?.closest('.filter-card')?.querySelector('.row');
    if (issueControls && !byId('downloadIssueStatusesBtn')) {
      const download = document.createElement('button');
      download.id = 'downloadIssueStatusesBtn';
      download.className = 'mini';
      download.textContent = 'Скачать статусы';
      download.onclick = downloadIssueStatuses;
      issueControls.appendChild(download);

      const upload = document.createElement('button');
      upload.id = 'loadIssueStatusesBtn';
      upload.className = 'mini';
      upload.textContent = 'Загрузить статусы';
      upload.onclick = () => byId('issueStatusFile').click();
      issueControls.appendChild(upload);

      const input = document.createElement('input');
      input.id = 'issueStatusFile';
      input.type = 'file';
      input.accept = '.json,application/json';
      input.hidden = true;
      input.onchange = event => {
        const file = event.target.files?.[0];
        if (file) importIssueStatuses(file);
        event.target.value = '';
      };
      issueControls.appendChild(input);
    }
  }

  function postProcessMap() {
    const focus = getNode(state.focusedNodeId);
    const selected = selectedIssue();
    const cards = [...document.querySelectorAll('[data-node-id]')];

    cards.forEach(card => {
      card.classList.remove('related-focus', 'focus-dim', 'issue-context-dim');
      card.style.removeProperty('--related-color');
      const node = getNode(card.dataset.nodeId);
      if (!node) return;

      const roles = sharedRoleIds(node);
      const meta = card.querySelector('.card-meta');
      if (roles.length > 1 && meta && !meta.querySelector('.shared-badge')) {
        const badge = document.createElement('span');
        badge.className = 'shared-badge';
        badge.textContent = `${roles.length} БР`;
        badge.title = `Общая реализация: ${roles.map(id => model.roles[id]?.label || id).join(', ')}`;
        meta.appendChild(badge);
      }
    });

    if (focus && !selected) {
      const edges = computeFocusEdges(focus);
      const related = new Map();
      edges.forEach(edge => {
        const other = edge.from === focus.id ? edge.to : edge.from;
        if (!related.has(other)) related.set(other, []);
        related.get(other).push(edge.compId);
      });
      cards.forEach(card => {
        if (card.dataset.nodeId === focus.id) return;
        if (related.has(card.dataset.nodeId)) {
          const compId = related.get(card.dataset.nodeId)[0];
          card.classList.add('related-focus');
          card.style.setProperty('--related-color', compColor(compId));
        } else {
          card.classList.add('focus-dim');
        }
      });
    }

    if (selected) {
      const context = issueContextNodeIds(selected);
      cards.forEach(card => {
        if (!context.has(card.dataset.nodeId)) card.classList.add('issue-context-dim');
      });
    }

    document.querySelectorAll('.semester').forEach(section => {
      section.classList.remove('sem-issue', 'source_mismatch', 'mapping_ambiguity', 'import_technical');
      const sem = Number(section.dataset.sem);
      const issues = activeSemesterIssues(state.roleId, sem);
      const head = section.querySelector('.sem-head');
      if (head && !head.querySelector('.sem-head-row')) {
        const strong = head.querySelector('strong');
        const span = head.querySelector('span');
        const row = document.createElement('div');
        row.className = 'sem-head-row';
        if (strong) row.appendChild(strong);
        head.insertBefore(row, span || null);
      }
      const row = head?.querySelector('.sem-head-row');
      row?.querySelector('.sem-issue-badge')?.remove();
      if (issues.length && row) {
        const badge = document.createElement('span');
        badge.className = 'sem-issue-badge';
        badge.textContent = String(issues.length);
        badge.title = `Открытые проблемы семестра: ${issues.length}`;
        row.appendChild(badge);
      }
      const selectedHere = selected?.semester_ids?.includes(sem) && selected.role_ids?.includes(state.roleId);
      if ((state.onlyIssues && issues.length) || selectedHere) {
        const type = selectedHere ? selected.type : issues[0].type;
        section.classList.add('sem-issue', type);
      }
    });
  }

  const originalRenderMap = renderMap;
  renderMap = function rc2RenderMap() {
    originalRenderMap();
    requestAnimationFrame(() => {
      document.querySelectorAll('[data-node-id]').forEach(card => {
        card.onclick = () => {
          const id = card.dataset.nodeId;
          state.focusedNodeId = state.focusedNodeId === id && !state.selectedIssueId ? null : id;
          state.selectedIssueId = null;
          state.tab = 'details';
          renderAll();
        };
      });
      postProcessMap();
      requestAnimationFrame(drawLines);
    });
  };

  function relatedDisciplineMap(node) {
    const related = computeFocusEdges(node);
    const map = new Map();
    related.forEach(edge => {
      const otherId = edge.from === node.id ? edge.to : edge.from;
      if (!map.has(otherId)) map.set(otherId, []);
      map.get(otherId).push(edge.compId);
    });
    return map;
  }

  function compactIssueButton(issue) {
    const meta = TYPE_META[issue.type];
    const normalized = issue.status !== 'open';
    return `<button class='issue-card ${issue.type} ${normalized ? 'normalized' : ''}' data-issue-id='${issue.issue_id}'>` +
      `<span class='priority-pill'>${issue.priority}</span>` +
      `<span class='type-pill'>${meta.icon} ${meta.label}</span>` +
      `<span class='status-pill ${issue.status}'>${STATUS_LABELS[issue.status]}</span>` +
      `<strong>${issue.short_message}</strong>` +
      `<small>${issueContextLabel(issue)} · ${issueSemesterLabel(issue)} · ${issueRoleLabel(issue)}</small>` +
      `</button>`;
  }

  renderDetailsPanel = function rc2RenderDetailsPanel() {
    const node = getNode(state.focusedNodeId);
    if (!node) {
      byId('panel').innerHTML = `<div class='empty'><b>Выберите дисциплину.</b><br>` +
        `При выбранной компетенции карточки показывают все её вхождения без недоказанных линий. ` +
        `Линии строятся только после выбора конкретной дисциплины.</div>`;
      return;
    }

    const selected = visibleCompIds(node);
    const full = Object.keys(node.competencies);
    const related = relatedDisciplineMap(node);
    const issues = nodeIssues(node.id);
    const roleIds = sharedRoleIds(node);
    const sharedBlock = roleIds.length > 1
      ? `<div class='rc2-common-block'><strong>Общая реализация для ${roleIds.length} бизнес-ролей</strong>` +
        `${roleIds.map(id => `• ${model.roles[id]?.label || id}`).join('<br>')}<br>` +
        `<span class='sub'>Семестр: ${node.semester} · фактические часы: ${node.hours}. Правило идентичности: нормализованное название + семестр + часы.</span></div>`
      : `<div class='sub'>Отдельная реализация выбранной бизнес-роли.</div>`;

    const relatedHtml = [...related.entries()].map(([id, compIds]) => {
      const other = getNode(id);
      const rows = compIds.map(compId => {
        const comp = catalogMap.get(compId);
        return `<span class='chip ${lineStyleForComp(compId) === 'dashed' ? 'dashed' : ''}' style='color:${compColor(compId)}'>` +
          `${comp.code}: ${node.competencies[compId]} → ${other.competencies[compId]}</span>`;
      }).join('');
      return `<button class='node-link' data-related-node='${id}'><b>${other.name}</b>` +
        `<small>${other.semester} семестр · ${other.hours} ч.</small><div class='related-codes'>${rows}</div></button>`;
    }).join('');

    byId('panel').innerHTML = `<h2>${node.name}</h2>` +
      `<div class='sub'>${node.code} · ${node.semester} семестр · ${node.hours} ч.</div>` +
      `<div class='rc2-focus-actions'><button id='panelClearFocus' class='rc2-action-button'>Снять фокус</button></div>` +
      sharedBlock +
      `<dl class='facts'><dt>Бизнес-роль</dt><dd>${model.roles[node.role_id].label}</dd>` +
      `<dt>Каноническая дисциплина</dt><dd>${node.canonical_id}</dd></dl>` +
      `<h3>Выбранные компетенции</h3>` +
      (selected.length ? `<div class='chips'>${selected.map(id => `<span class='chip ${lineStyleForComp(id) === 'dashed' ? 'dashed' : ''}' style='color:${compColor(id)}'>${catalogMap.get(id).code} · ${node.competencies[id]}</span>`).join('')}</div>` : `<div class='empty'>В активном фильтре нет компетенций этой дисциплины.</div>`) +
      `<details class='full-comps'><summary>Полный набор дисциплины · ${full.length}</summary><div class='chips'>${full.map(id => `<span class='chip ${lineStyleForComp(id) === 'dashed' ? 'dashed' : ''}' style='color:${compColor(id)}'>${catalogMap.get(id).code} · ${node.competencies[id]}</span>`).join('')}</div></details>` +
      `<h3>Проблемы дисциплины</h3><div class='node-issue-list'>${issues.length ? issues.map(compactIssueButton).join('') : `<div class='empty'>Связанных проблем нет.</div>`}</div>` +
      `<h3>Связанные дисциплины</h3><div class='rc2-notice'>Линия означает только наличие одной и той же компетенции в двух дисциплинах. Она не является пререквизитом или постреквизитом.</div>` +
      `<div class='related-list'>${relatedHtml || `<div class='empty'>Связанные дисциплины не найдены в текущем активном наборе.</div>`}</div>` +
      `<h3>Источники</h3><table class='source-table'><tr><th>Источник</th><th>Значение</th></tr>` +
      `<tr><td>Стыковочный УП</td><td>${node.name} · ${node.hours} ч.</td></tr>` +
      `<tr><td>Матрица</td><td>${full.length} компетенций</td></tr></table>`;

    byId('panelClearFocus').onclick = () => {
      state.focusedNodeId = null;
      renderAll();
    };
    byId('panel').querySelectorAll('[data-related-node]').forEach(button => button.onclick = () => {
      state.focusedNodeId = button.dataset.relatedNode;
      state.selectedIssueId = null;
      state.tab = 'details';
      renderAll();
      scrollToNode(button.dataset.relatedNode);
    });
    byId('panel').querySelectorAll('[data-issue-id]').forEach(button => button.onclick = () => focusIssue(button.dataset.issueId));
  };

  function issueDiagnosticBody(issue) {
    const meta = TYPE_META[issue.type];
    const id = safeId(issue.issue_id);
    return `<div class='issue-body'>` +
      `<div><span class='priority-pill'>${issue.priority}</span><span class='type-pill'>${meta.label}</span><span class='status-pill ${issue.status}'>${STATUS_LABELS[issue.status]}</span></div>` +
      `<div class='diagnostic-label'>Правило</div><div class='diagnostic-value'>${issue.rule_id}</div>` +
      `<div class='diagnostic-label'>Полный смысл</div><div class='diagnostic-value'>${issue.full_description}</div>` +
      `<div class='diagnostic-label'>Текущее состояние</div><div class='diagnostic-value'>${issue.current_state}</div>` +
      `<div class='diagnostic-label'>Ожидаемое состояние</div><div class='diagnostic-value'>${issue.expected_state}</div>` +
      `<div class='diagnostic-label'>Требуемое действие</div><div class='diagnostic-value'>${issue.required_action}</div>` +
      `<div class='diagnostic-label'>Контекст</div><div class='diagnostic-value'>${issueContextLabel(issue)} · ${issueSemesterLabel(issue)} · ${issueRoleLabel(issue)}</div>` +
      `<details class='full-comps'><summary>Источники и узлы</summary><div class='diagnostic-value'>${(issue.source_refs || []).join('<br>') || '—'}<br>` +
      `основные: ${(issue.primary_node_ids || []).length} · существующие: ${(issue.existing_node_ids || []).length} · кандидаты: ${(issue.candidate_node_ids || []).length} · связанные: ${(issue.related_node_ids || []).length}</div></details>` +
      `<textarea class='comment' id='issueComment-${id}' placeholder='Комментарий обязателен для закрытия'>${issue.comment || ''}</textarea>` +
      `<div class='rc2-status-row'>` +
      `<button data-rc2-status='fixed' data-issue='${issue.issue_id}'>Исправлена во внешнем источнике</button>` +
      `<button data-rc2-status='normalized' data-issue='${issue.issue_id}'>Нормализована по решению</button>` +
      `<button data-rc2-status='not_relevant' data-issue='${issue.issue_id}'>Не актуальна</button>` +
      `<button data-rc2-status='open' data-issue='${issue.issue_id}'>Вернуть в работу</button>` +
      `</div>` +
      (issue.history?.length ? `<details class='full-comps'><summary>История статусов · ${issue.history.length}</summary><pre>${escapeHtml(JSON.stringify(issue.history, null, 2))}</pre></details>` : '') +
      `</div>`;
  }

  function accordionIssueItem(issue) {
    const meta = TYPE_META[issue.type];
    const normalized = issue.status !== 'open';
    const expanded = issue.issue_id === state.selectedIssueId;
    const viewed = state.viewedIssueIds.has(issue.issue_id);
    return `<div id='issue-item-${safeId(issue.issue_id)}' class='issue-card rc2-item ${issue.type} ${normalized ? 'normalized' : ''} ${expanded ? 'expanded' : ''}'>` +
      `<button class='issue-header' data-issue-id='${issue.issue_id}'>` +
      `<span class='priority-pill'>${issue.priority}</span><span class='type-pill'>${meta.icon} ${meta.label}</span>` +
      `<span class='status-pill ${issue.status}'>${STATUS_LABELS[issue.status]}</span>` +
      (viewed ? `<span class='viewed-mark'>просмотрено</span>` : '') +
      `<strong>${issue.short_message}</strong>` +
      `<span class='issue-context'>${issueContextLabel(issue)} · ${issueSemesterLabel(issue)} · ${issueRoleLabel(issue)}</span>` +
      `</button>${expanded ? issueDiagnosticBody(issue) : ''}</div>`;
  }

  renderIssuesPanel = function rc2RenderIssuesPanel() {
    const issues = allIssues().filter(issueVisible);
    const open = issues.filter(issue => issue.status === 'open');
    const normalized = issues.filter(issue => issue.status !== 'open');
    const counts = Object.keys(TYPE_META).map(type => `${TYPE_META[type].icon} ${open.filter(issue => issue.type === type).length}`).join(' · ');
    const selectedNormalized = normalized.some(issue => issue.issue_id === state.selectedIssueId);

    byId('panel').innerHTML = `<div class='rc2-issue-summary'><span class='metric'>${counts}</span><span class='metric'>серые: ${normalized.length}</span></div>` +
      `<div class='rc2-type-legend'>${Object.keys(TYPE_META).map(type => `<span class='type-pill'>${TYPE_META[type].icon} ${TYPE_META[type].label}</span>`).join('')}</div>` +
      `<div class='rc2-status-info'>Клик раскрывает карточку на месте. Порядок списка не меняется. Закрытие фиксирует работу во внешнем УП или матрице и требует комментарий.</div>` +
      `<h3>Открытые · ${open.length}</h3><div class='rc2-accordion-list'>${open.map(accordionIssueItem).join('') || `<div class='empty'>Открытых проблем нет.</div>`}</div>` +
      `<details class='full-comps' ${selectedNormalized ? 'open' : ''}><summary>Нормализованные · ${normalized.length}</summary><div class='rc2-accordion-list'>${normalized.map(accordionIssueItem).join('') || `<div class='empty'>Нормализованных записей нет.</div>`}</div></details>`;

    byId('panel').querySelectorAll('.issue-header[data-issue-id]').forEach(button => button.onclick = () => focusIssue(button.dataset.issueId));
    byId('panel').querySelectorAll('[data-rc2-status]').forEach(button => button.onclick = event => {
      event.stopPropagation();
      const issueId = button.dataset.issue;
      const comment = byId(`issueComment-${safeId(issueId)}`)?.value || '';
      if (setIssueStatus(issueId, button.dataset.rc2Status, comment, 'manual_external')) {
        state.selectedIssueId = issueId;
        state.tab = 'issues';
        persistIssueStatuses();
        requestAnimationFrame(() => byId(`issue-item-${safeId(issueId)}`)?.scrollIntoView({block: 'nearest'}));
      }
    });
  };

  focusIssue = function rc2FocusIssue(issueId) {
    const issue = allIssues().find(item => item.issue_id === issueId);
    if (!issue) return;
    state.selectedIssueId = issueId;
    state.viewedIssueIds.add(issueId);
    state.tab = 'issues';
    if (issue.role_ids?.length && !issue.role_ids.includes(state.roleId)) state.roleId = issue.role_ids[0];
    if (issue.competency_id) state.activeCompIds.add(issue.competency_id);
    const target = [...(issue.primary_node_ids || []), ...(issue.existing_node_ids || []), ...(issue.candidate_node_ids || [])]
      .find(id => getNode(id)?.role_id === state.roleId);
    state.focusedNodeId = target || null;
    renderAll();
    requestAnimationFrame(() => {
      byId(`issue-item-${safeId(issueId)}`)?.scrollIntoView({behavior: 'smooth', block: 'nearest'});
      if (target) scrollToNode(target);
      else if (issue.semester_ids?.length) scrollToSemester(issue.semester_ids[0]);
    });
  };

  const originalSetIssueStatus = setIssueStatus;
  setIssueStatus = function rc2SetIssueStatus(issueId, status, comment, method = 'manual_external') {
    const result = originalSetIssueStatus(issueId, status, comment, method);
    if (result) persistIssueStatuses();
    return result;
  };

  autosave = function rc2Autosave() {
    persistIssueStatuses();
  };

  const originalResetAll = resetAll;
  resetAll = function rc2ResetAll() {
    localStorage.removeItem(STATUS_STORAGE_KEY);
    return originalResetAll();
  };

  function dynamicProfileProjection(profile, catalog) {
    return profile.groups.map(group => ({
      id: group.id,
      label: group.label,
      competency_ids: catalog.filter(comp => comp.group_id === group.id).map(comp => comp.id),
      line_style: group.line_style,
    }));
  }

  function runRc2ConformanceTests() {
    const results = [];
    const test = (id, fn) => {
      try {
        const detail = fn();
        results.push({id, ok: true, detail: detail || 'OK'});
      } catch (error) {
        results.push({id, ok: false, detail: error.message});
      }
    };

    test('RC2-FEATURES-01', () => {
      const visible = ['editBtn', 'saveSessionBtn', 'loadSessionBtn', 'snapshotBtn', 'changesBtn'].filter(id => !byId(id)?.classList.contains('rc2-hidden'));
      if (visible.length) throw new Error(`Не скрыты: ${visible.join(', ')}`);
    });
    test('RC2-GLOBAL-LINES-01', () => {
      if (computeGlobalEdges().length !== 0) throw new Error('Глобальные линии без фокуса не отключены');
    });
    test('RC2-SHARED-01', () => {
      const node = nodeByKey('cyber', 's1-rus');
      if (sharedRoleIds(node).length !== 2) throw new Error('Общая дисциплина не определена по названию, семестру и часам');
    });
    test('RC2-STATUS-01', () => {
      if (!issueStatusPayloadCompatible(issueStatusPayload())) throw new Error('Файл статусов несовместим сам с собой');
    });
    test('RC2-ZERO-01', () => {
      if (!allNodes().some(node => node.hours === 0)) throw new Error('Нет тестового узла с нулевыми часами');
    });
    test('RC2-DYNAMIC-CATALOG-01', () => {
      const altProfile = {groups: [{id: 'alpha', label: 'A', line_style: 'solid'}, {id: 'beta', label: 'B', line_style: 'none'}, {id: 'gamma', label: 'C', line_style: 'dashed'}]};
      const altCatalog = [{id: 'a1', group_id: 'alpha'}, {id: 'b1', group_id: 'beta'}, {id: 'g1', group_id: 'gamma'}, {id: 'g2', group_id: 'gamma'}];
      const projection = dynamicProfileProjection(altProfile, altCatalog);
      if (projection.length !== 3 || projection[2].competency_ids.length !== 2) throw new Error('Ядро зависит от фиксированного числа групп');
    });
    test('RC2-FOCUS-01', () => {
      const node = nodeByKey('cyber', 's3-networks');
      if (!computeFocusEdges(node, new Set()).length) throw new Error('Фокус дисциплины не строит подтверждённые общие связи');
    });

    window.__RC2_CONFORMANCE_RESULTS__ = results;
    const ok = results.every(result => result.ok);
    document.documentElement.dataset.rc2SelfTest = ok ? 'ok' : 'failed';
    document.documentElement.dataset.rc2Ready = '1';
    return results;
  }

  addToolbarControls();
  ensureZeroHourFixtures();
  rebuildIssues();
  restoreIssueStatuses();

  document.addEventListener('keydown', event => {
    if (event.key === 'Escape' && state.focusedNodeId) {
      state.focusedNodeId = null;
      state.selectedIssueId = null;
      state.tab = 'details';
      renderAll();
    }
  });

  window.__RUN_RC2_CONFORMANCE_TESTS__ = runRc2ConformanceTests;
  window.__TRAJECTORY_REFERENCE_RC2__ = {
    version: RC2_VERSION,
    sharedPeers,
    sharedRoleIds,
    issueStatusPayload,
    issueStatusPayloadCompatible,
    dynamicProfileProjection,
  };

  renderAll();
  requestAnimationFrame(() => {
    postProcessMap();
    runRc2ConformanceTests();
  });
})();
