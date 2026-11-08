/* Group Chat Live Polling & Interactive Messaging */
(function () {
  var box = document.getElementById('chatBox');
  var stream = document.getElementById('chatStream');
  var form = document.getElementById('chatForm');
  if (!box || !stream || !form) { return; }

  var textarea = form.querySelector('textarea');
  var tripId = box.dataset.tripId;
  var myId = parseInt(box.dataset.userId, 10);
  var csrfToken = form.querySelector('input[name="csrfmiddlewaretoken"]')?.value || '';
  var statusDot = document.getElementById('chat-status-dot');
  var statusText = document.getElementById('chat-status');
  var emptyNotice = document.getElementById('emptyNotice');

  var renderedIds = new Set();
  var lastMsgId = 0;

  // Collect initial rendered message IDs
  stream.querySelectorAll('.msg-bubble[data-msg-id]').forEach(function (el) {
    var id = parseInt(el.dataset.msgId, 10);
    if (id) {
      renderedIds.add(id);
      if (id > lastMsgId) { lastMsgId = id; }
    }
  });

  function scrollDown() {
    stream.scrollTop = stream.scrollHeight;
  }
  scrollDown();

  function setStatus(text, color) {
    if (statusText) {
      statusText.textContent = text;
      statusText.style.color = color;
    }
    if (statusDot) {
      statusDot.style.background = color;
      statusDot.style.boxShadow = '0 0 8px ' + color;
    }
  }

  function renderMessage(data) {
    if (data.id && renderedIds.has(data.id)) { return; }
    if (data.id) {
      renderedIds.add(data.id);
      if (data.id > lastMsgId) { lastMsgId = data.id; }
    }

    if (emptyNotice) {
      emptyNotice.remove();
      emptyNotice = null;
    }

    var isMine = (data.sender_id === myId);
    var bubble = document.createElement('div');
    bubble.className = 'msg-bubble ' + (isMine ? 'msg-mine' : 'msg-theirs');
    if (data.id) { bubble.dataset.msgId = data.id; }

    var header = document.createElement('div');
    header.style.display = 'flex';
    header.style.alignItems = 'center';
    header.style.gap = '8px';
    header.style.marginBottom = '6px';

    if (data.photo) {
      var img = document.createElement('img');
      img.src = data.photo;
      img.alt = '';
      img.style.width = '20px';
      img.style.height = '20px';
      img.style.borderRadius = '50%';
      img.style.objectFit = 'cover';
      header.appendChild(img);
    } else {
      var initial = document.createElement('span');
      initial.style.width = '20px';
      initial.style.height = '20px';
      initial.style.borderRadius = '50%';
      initial.style.background = 'rgba(255,255,255,0.15)';
      initial.style.display = 'inline-flex';
      initial.style.alignItems = 'center';
      initial.style.justifyContent = 'center';
      initial.style.fontSize = '10px';
      initial.style.fontWeight = '700';
      initial.textContent = (data.sender || 'U').charAt(0).toUpperCase();
      header.appendChild(initial);
    }

    var name = document.createElement('strong');
    name.style.fontSize = '13px';
    name.textContent = isMine ? 'You' : data.sender;
    header.appendChild(name);

    var time = document.createElement('small');
    time.style.opacity = '0.7';
    time.style.fontSize = '11px';
    time.textContent = data.time || '';
    header.appendChild(time);

    bubble.appendChild(header);

    var body = document.createElement('div');
    body.style.lineHeight = '1.5';
    body.style.whiteSpace = 'pre-wrap';
    body.textContent = data.text;
    bubble.appendChild(body);

    stream.appendChild(bubble);
    scrollDown();
  }

  // Live polling for incoming messages
  function pollNewMessages() {
    var url = '/chat/' + tripId + '/messages/?after=' + lastMsgId;
    fetch(url)
      .then(function (res) {
        if (!res.ok) { throw new Error('Status ' + res.status); }
        return res.json();
      })
      .then(function (result) {
        if (result.messages && result.messages.length > 0) {
          result.messages.forEach(renderMessage);
        }
        setStatus('Live', '#4ade80');
      })
      .catch(function () {
        setStatus('Reconnecting...', '#fbbf24');
      });
  }

  var pollInterval = setInterval(pollNewMessages, 2500);

  // Asynchronous Send
  var isSending = false;
  form.addEventListener('submit', function (event) {
    if (!textarea) { return; }
    var text = textarea.value.trim();
    if (!text || isSending) {
      event.preventDefault();
      return;
    }

    event.preventDefault();
    isSending = true;

    var formData = new FormData();
    formData.append('text', text);
    formData.append('csrfmiddlewaretoken', csrfToken);

    textarea.value = '';

    fetch(window.location.href, {
      method: 'POST',
      headers: {
        'X-Requested-With': 'XMLHttpRequest',
      },
      body: formData,
    })
      .then(function (res) {
        if (!res.ok) { throw new Error('Send failed'); }
        return res.json();
      })
      .then(function (data) {
        renderMessage(data);
      })
      .catch(function (err) {
        // If AJAX fails, restore text
        textarea.value = text;
      })
      .finally(function () {
        isSending = false;
        textarea.focus();
      });
  });

  // Enter sends, Shift+Enter makes new line
  if (textarea) {
    textarea.addEventListener('keydown', function (event) {
      if (event.key === 'Enter' && !event.shiftKey) {
        event.preventDefault();
        form.requestSubmit();
      }
    });
  }
})();

