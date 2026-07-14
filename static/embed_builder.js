const guildId = document.querySelector('.embed-builder').dataset.guildId;
let mentionables = { users: [], roles: [], channels: [] };
let fields = [];

async function loadMentionables() {
  const res = await fetch(`/api/guild/${guildId}/mentionables`);
  mentionables = await res.json();
  const channelSelect = document.getElementById('eb-channel');
  channelSelect.innerHTML = mentionables.channels.map(c => `<option value="${c.id}">#${c.name}</option>`).join('');
}
loadMentionables();

function updatePreview() {
  document.getElementById('preview-author').textContent = document.getElementById('eb-author').value;
  document.getElementById('preview-title').textContent = document.getElementById('eb-title').value;
  document.getElementById('preview-desc').textContent = document.getElementById('eb-description').value;
  document.getElementById('preview-footer').textContent = document.getElementById('eb-footer').value;
  document.getElementById('eb-preview').querySelector('.discord-embed-bar').style.background = document.getElementById('eb-color').value;
  const img = document.getElementById('preview-image');
  const imgUrl = document.getElementById('eb-image').value;
  if (imgUrl) { img.src = imgUrl; img.classList.remove('hidden'); } else { img.classList.add('hidden'); }
  const fieldsBox = document.getElementById('preview-fields');
  fieldsBox.innerHTML = fields.map(f => `<div class="discord-embed-field"><div class="discord-embed-field-name">${f.name}</div><div class="discord-embed-field-value">${f.value}</div></div>`).join('');
}

['eb-title', 'eb-description', 'eb-author', 'eb-footer', 'eb-color', 'eb-image'].forEach(id => {
  document.getElementById(id).addEventListener('input', updatePreview);
});

function addField() {
  const idx = fields.length;
  fields.push({ name: '', value: '', inline: false });
  const div = document.createElement('div');
  div.innerHTML = `
    <label>Field Name</label><input onchange="fields[${idx}].name=this.value; updatePreview();" />
    <label>Field Value</label><input onchange="fields[${idx}].value=this.value; updatePreview();" />
  `;
  document.getElementById('eb-fields').appendChild(div);
}

// @ / # mention autocomplete on the description textarea
const descBox = document.getElementById('eb-description');
const autoBox = document.getElementById('eb-autocomplete');
descBox.addEventListener('input', () => {
  const val = descBox.value;
  const cursor = descBox.selectionStart;
  const upToCursor = val.slice(0, cursor);
  const match = upToCursor.match(/([@#])(\w*)$/);
  if (!match) { autoBox.classList.add('hidden'); return; }
  const [, symbol, query] = match;
  const list = symbol === '@'
    ? mentionables.users.filter(u => u.name.toLowerCase().includes(query.toLowerCase()))
    : mentionables.channels.filter(c => c.name.toLowerCase().includes(query.toLowerCase()));
  if (!list.length) { autoBox.classList.add('hidden'); return; }
  autoBox.innerHTML = list.slice(0, 8).map(item =>
    `<div class="autocomplete-item" onclick="insertMention('${symbol}', '${item.name}', ${match.index})">${symbol}${item.name}</div>`
  ).join('');
  autoBox.classList.remove('hidden');
});

function insertMention(symbol, name, matchIndex) {
  const val = descBox.value;
  const cursor = descBox.selectionStart;
  descBox.value = val.slice(0, matchIndex) + symbol + name + ' ' + val.slice(cursor);
  autoBox.classList.add('hidden');
  updatePreview();
}

function exportJSON() {
  const box = document.getElementById('eb-json');
  box.value = JSON.stringify(buildPayload(), null, 2);
  box.classList.remove('hidden');
}

function importJSON() {
  const box = document.getElementById('eb-json');
  box.classList.remove('hidden');
  box.addEventListener('change', () => {
    try {
      const data = JSON.parse(box.value);
      document.getElementById('eb-title').value = data.title || '';
      document.getElementById('eb-description').value = data.description || '';
      document.getElementById('eb-author').value = data.author || '';
      document.getElementById('eb-footer').value = data.footer || '';
      document.getElementById('eb-image').value = data.image_url || '';
      fields = data.fields || [];
      updatePreview();
    } catch (e) { alert('Invalid JSON'); }
  }, { once: true });
}

function buildPayload() {
  return {
    channel_id: document.getElementById('eb-channel').value,
    title: document.getElementById('eb-title').value,
    description: document.getElementById('eb-description').value,
    author: document.getElementById('eb-author').value,
    footer: document.getElementById('eb-footer').value,
    color: document.getElementById('eb-color').value,
    image_url: document.getElementById('eb-image').value,
    fields,
  };
}

async function sendEmbed() {
  const res = await fetch(`/api/guild/${guildId}/send-embed`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(buildPayload()),
  });
  const data = await res.json();
  alert(data.ok ? 'Embed sent!' : 'Failed: ' + data.error);
}
