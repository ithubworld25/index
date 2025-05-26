import html
from typing import List, Dict, Tuple


def _guess_actor_and_action(line: str) -> Tuple[str, str]:
    """Best-effort heuristic to detect actor and action."""
    parts = line.split()
    if len(parts) > 1:
        actor = parts[0].rstrip(',').capitalize()
        action = " ".join(parts[1:])
    else:
        actor = "Actor"
        action = line
    return actor, action

def parse_text(text: str) -> Tuple[Dict[str, List[str]], List[Dict[str, str]]]:
    """Parse raw text into lanes and tasks."""
    lanes: Dict[str, List[str]] = {}
    tasks: List[Dict[str, str]] = []
    lines = [ln.strip() for ln in text.splitlines() if ln.strip()]
    for i, line in enumerate(lines):
        actor = 'Actor'
        action = line
        if ':' in line:
            a, t = line.split(':', 1)
            if t.strip():
                actor = a.strip()
                action = t.strip()
        else:
            actor, action = _guess_actor_and_action(line)
        task_id = f"Task_{i+1}"
        tasks.append({'id': task_id, 'name': action, 'actor': actor})
        lanes.setdefault(actor, []).append(task_id)
    return lanes, tasks

def generate_bpmn(text: str) -> str:
    lanes, tasks = parse_text(text)
    lines = []
    lines.append('<?xml version="1.0" encoding="UTF-8"?>')
    lines.append('<bpmn:definitions xmlns:bpmn="http://www.omg.org/spec/BPMN/20100524/MODEL"')
    lines.append('                   xmlns:bpmndi="http://www.omg.org/spec/BPMN/20100524/DI"')
    lines.append('                   xmlns:dc="http://www.omg.org/spec/DD/20100524/DC"')
    lines.append('                   xmlns:di="http://www.omg.org/spec/DD/20100524/DI"')
    lines.append('                   id="Definitions_1" targetNamespace="http://bpmn.io/schema/bpmn">')
    lines.append('  <bpmn:collaboration id="Collaboration_1">')
    lines.append('    <bpmn:participant id="Participant_Process" processRef="Process_1" />')
    lines.append('  </bpmn:collaboration>')
    lines.append('  <bpmn:process id="Process_1" isExecutable="false">')
    lines.append('    <bpmn:laneSet id="LaneSet_1">')
    for actor, tids in lanes.items():
        lane_id = f"Lane_{actor.replace(' ', '_')}"
        lines.append(f'      <bpmn:lane id="{lane_id}" name="{html.escape(actor)}">')
        for tid in tids:
            lines.append(f'        <bpmn:flowNodeRef>{tid}</bpmn:flowNodeRef>')
        lines.append('      </bpmn:lane>')
    lines.append('    </bpmn:laneSet>')
    lines.append('    <bpmn:startEvent id="StartEvent_1" name="Start" />')
    for t in tasks:
        lines.append(f'    <bpmn:task id="{t["id"]}" name="{html.escape(t["name"])}" />')
    lines.append('    <bpmn:endEvent id="EndEvent_1" name="End" />')
    if tasks:
        lines.append('    <bpmn:sequenceFlow id="Flow_Start_Task1" sourceRef="StartEvent_1" targetRef="Task_1" />')
        for i in range(len(tasks)-1):
            lines.append(f'    <bpmn:sequenceFlow id="Flow_{i+1}_{i+2}" sourceRef="Task_{i+1}" targetRef="Task_{i+2}" />')
        lines.append(f'    <bpmn:sequenceFlow id="Flow_Last_End" sourceRef="Task_{len(tasks)}" targetRef="EndEvent_1" />')
    else:
        lines.append('    <bpmn:sequenceFlow id="Flow_Start_End" sourceRef="StartEvent_1" targetRef="EndEvent_1" />')
    lines.append('  </bpmn:process>')
    lines.append('  <bpmndi:BPMNDiagram id="BPMNDiagram_1">')
    lines.append('    <bpmndi:BPMNPlane id="BPMNPlane_1" bpmnElement="Process_1">')
    # layout
    x = 100
    y = 100
    lines.append('      <bpmndi:BPMNShape id="StartEvent_1_di" bpmnElement="StartEvent_1">')
    lines.append(f'        <dc:Bounds x="{x}" y="{y}" width="36" height="36"/>')
    lines.append('      </bpmndi:BPMNShape>')
    task_x = x + 80
    for t in tasks:
        lines.append(f'      <bpmndi:BPMNShape id="{t["id"]}_di" bpmnElement="{t["id"]}">')
        lines.append(f'        <dc:Bounds x="{task_x}" y="{y-18}" width="100" height="80"/>')
        lines.append('      </bpmndi:BPMNShape>')
        task_x += 150
    lines.append('      <bpmndi:BPMNShape id="EndEvent_1_di" bpmnElement="EndEvent_1">')
    lines.append(f'        <dc:Bounds x="{task_x}" y="{y}" width="36" height="36"/>')
    lines.append('      </bpmndi:BPMNShape>')
    # sequence edges
    if tasks:
        lines.append('      <bpmndi:BPMNEdge id="Flow_Start_Task1_di" bpmnElement="Flow_Start_Task1">')
        lines.append(f'        <di:waypoint x="{x+36}" y="{y+18}"/>')
        lines.append(f'        <di:waypoint x="{100+80}" y="{y+18}"/>')
        lines.append('      </bpmndi:BPMNEdge>')
        edge_x = 100 + 80
        for i in range(len(tasks)-1):
            lines.append(f'      <bpmndi:BPMNEdge id="Flow_{i+1}_{i+2}_di" bpmnElement="Flow_{i+1}_{i+2}">')
            lines.append(f'        <di:waypoint x="{edge_x+100}" y="{y+18}"/>')
            lines.append(f'        <di:waypoint x="{edge_x+150}" y="{y+18}"/>')
            lines.append('      </bpmndi:BPMNEdge>')
            edge_x += 150
        lines.append('      <bpmndi:BPMNEdge id="Flow_Last_End_di" bpmnElement="Flow_Last_End">')
        lines.append(f'        <di:waypoint x="{edge_x+100}" y="{y+18}"/>')
        lines.append(f'        <di:waypoint x="{edge_x+150}" y="{y+18}"/>')
        lines.append('      </bpmndi:BPMNEdge>')
    else:
        lines.append('      <bpmndi:BPMNEdge id="Flow_Start_End_di" bpmnElement="Flow_Start_End">')
        lines.append(f'        <di:waypoint x="{x+36}" y="{y+18}"/>')
        lines.append(f'        <di:waypoint x="{task_x}" y="{y+18}"/>')
        lines.append('      </bpmndi:BPMNEdge>')
    lines.append('    </bpmndi:BPMNPlane>')
    lines.append('  </bpmndi:BPMNDiagram>')
    lines.append('</bpmn:definitions>')
    return '\n'.join(lines)

if __name__ == '__main__':
    import sys
    text = sys.stdin.read()
    print(generate_bpmn(text))
