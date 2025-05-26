const modeler = new BpmnJS({ container: '#canvas' });

document.getElementById('generate').addEventListener('click', async () => {
  const text = document.getElementById('input').value;
  const resp = await fetch('/parse', {
    method: 'POST',
    body: text
  });
  const data = await resp.json();
  if (data.bpmn) {
    modeler.importXML(data.bpmn);
  }
});

document.getElementById('download').addEventListener('click', async () => {
  const result = await modeler.saveXML({ format: true });
  const blob = new Blob([result.xml], { type: 'application/bpmn20-xml' });
  const url = URL.createObjectURL(blob);
  const a = document.createElement('a');
  a.href = url;
  a.download = 'diagram.bpmn';
  a.click();
  URL.revokeObjectURL(url);
});
