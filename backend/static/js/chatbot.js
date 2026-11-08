/* AI Destination Assistant Floating Widget Logic */
(function () {
  var root = document.getElementById('chatbot');
  var toggle = document.getElementById('chatbot-toggle');
  var panel = document.getElementById('chatbot-panel');
  var closeButton = document.getElementById('chatbot-close');
  var messagesBox = document.getElementById('chatbot-messages');
  var form = document.getElementById('chatbot-form');
  var input = document.getElementById('chatbot-input');
  var sendButton = document.getElementById('chatbot-send');
  if (!root || !toggle || !panel || !form || !input || !sendButton) { return; }

  var history = [];
  var isSending = false;

  function addMessage(role, text) {
    var div = document.createElement('div');
    div.className = 'chatbot-msg chatbot-' + role;
    div.textContent = text;
    messagesBox.appendChild(div);
    messagesBox.scrollTop = messagesBox.scrollHeight;
    return div;
  }

  toggle.addEventListener('click', function () {
    panel.hidden = !panel.hidden;
    if (!panel.hidden) {
      if (messagesBox.children.length === 0) {
        addMessage('assistant', 'Hi! Ask me anything about a travel destination.');
      }
      input.focus();
    }
  });

  if (closeButton) {
    closeButton.addEventListener('click', function () {
      panel.hidden = true;
    });
  }

  form.addEventListener('submit', function (event) {
    event.preventDefault();
    if (isSending) { return; }
    var text = input.value.trim();
    if (!text) { return; }

    isSending = true;
    addMessage('user', text);
    input.value = '';
    var thinking = addMessage('assistant', 'Thinking...');
    sendButton.disabled = true;

    fetch(root.dataset.url, {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
        'X-CSRFToken': root.dataset.csrf
      },
      body: JSON.stringify({ message: text, history: history })
    })
      .then(function (response) {
        return response.json().then(function (data) {
          return { ok: response.ok, data: data };
        });
      })
      .then(function (result) {
        if (result.ok) {
          thinking.textContent = result.data.reply;
          history.push({ role: 'user', text: text });
          history.push({ role: 'assistant', text: result.data.reply });
          history = history.slice(-10);
        } else {
          thinking.textContent = result.data.error || 'Something went wrong.';
        }
      })
      .catch(function () {
        thinking.textContent = 'Could not reach the assistant. Please try again.';
      })
      .then(function () {
        isSending = false;
        sendButton.disabled = false;
        messagesBox.scrollTop = messagesBox.scrollHeight;
        input.focus();
      });
  });
})();

