/* Group Chat Live Adaptive Polling & Resilient Messaging */
(function () {
  'use strict';

  var box = document.getElementById('chatBox');
  var stream = document.getElementById('chatStream');
  var form = document.getElementById('chatForm');
  if (!box || !stream || !form) { return; }

  var textarea = form.querySelector('textarea');
  var submitBtn = document.getElementById('chatSubmit');
  var tripId = box.dataset.tripId;
  var myId = parseInt(box.dataset.userId, 10);
  var statusDot = document.getElementById('chat-status-dot');
  var statusText = document.getElementById('chat-status');
  var emptyNotice = document.getElementById('emptyNotice');
  var errorBanner = document.getElementById('chatErrorBanner');

  var renderedIds = new Set();
  var lastMsgId = 0;
  var consecutiveErrors = 0;
  var pollTimeoutId = null;
  var isPollingActive = true;
  var isSending = false;

  function getCsrfToken() {
    var input = form.querySelector('input[name="csrfmiddlewaretoken"]');
    if (input && input.value) { return input.value; }
    // Fallback to cookie
    var match = document.cookie.match(/(?:^|;\s*)csrftoken=([^;]+)/);
    return match ? decodeURIComponent(match[1]) : '';
  }

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

  function showError(msg) {
    if (!errorBanner) {
      errorBanner = document.createElement('div');
      errorBanner.id = 'chatErrorBanner';
      errorBanner.style.cssText = 'background: rgba(239, 68, 68, 0.15); border: 1px solid rgba(239, 68, 68, 0.4); color: #fca5a5; padding: 10px 16px; margin: 0 16px 12px; border-radius: 12px; font-size: 13px; display: flex; align-items: center; justify-content: space-between;';
      form.parentNode.insertBefore(errorBanner, form);
    }
    errorBanner.innerHTML = '<span>' + msg + '</span><button type="button" style="background: none; border: none; color: #fca5a5; cursor: pointer; font-size: 16px; line-height: 1; padding: 0 4px;">&times;</button>';
    errorBanner.querySelector('button').onclick = hideError;
    errorBanner.style.display = 'flex';
  }

  function hideError() {
    if (errorBanner) {
      errorBanner.style.display = 'none';
    }
  }

  function renderMessage(data) {
    if (!data) { return; }
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
    name.textContent = isMine ? 'You' : (data.sender || 'Member');
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
    body.textContent = data.text || '';
    bubble.appendChild(body);

    stream.appendChild(bubble);
    scrollDown();
  }

  /* Adaptive Polling loop with backoff and visibility handling */
  function scheduleNextPoll(delayMs) {
    if (!isPollingActive) { return; }
    if (pollTimeoutId) { clearTimeout(pollTimeoutId); }
    pollTimeoutId = setTimeout(pollNewMessages, delayMs);
  }

  function pollNewMessages() {
    if (!isPollingActive) { return; }
    var url = '/chat/' + tripId + '/messages/?after=' + lastMsgId;

    fetch(url, {
      headers: {
        'Accept': 'application/json',
        'X-Requested-With': 'XMLHttpRequest',
      },
    })
      .then(function (res) {
        if (!res.ok) {
          throw new Error('HTTP ' + res.status);
        }
        return res.json();
      })
      .then(function (result) {
        consecutiveErrors = 0;
        setStatus('Live', '#4ade80');
        hideError();

        if (result && Array.isArray(result.messages)) {
          result.messages.forEach(renderMessage);
        }

        // Standard poll interval when healthy
        scheduleNextPoll(3500);
      })
      .catch(function (err) {
        consecutiveErrors++;
        // Apply graceful backoff: 3.5s -> 6s -> 10s -> max 15s
        var nextDelay = Math.min(3500 + (consecutiveErrors * 2500), 15000);

        if (consecutiveErrors >= 3) {
          setStatus('Reconnecting...', '#fbbf24');
        }

        scheduleNextPoll(nextDelay);
      });
  }

  // Initial poll start
  scheduleNextPoll(3500);

  // Tab visibility changes: pause when hidden, immediately catch up on focus
  document.addEventListener('visibilitychange', function () {
    if (document.visibilityState === 'hidden') {
      isPollingActive = false;
      if (pollTimeoutId) { clearTimeout(pollTimeoutId); }
    } else {
      isPollingActive = true;
      consecutiveErrors = 0;
      pollNewMessages();
    }
  });

  /* Asynchronous Send */
  form.addEventListener('submit', function (event) {
    event.preventDefault();
    if (!textarea) { return; }

    var text = textarea.value.trim();
    if (!text || isSending) { return; }

    isSending = true;
    if (submitBtn) {
      submitBtn.disabled = true;
      submitBtn.style.opacity = '0.6';
    }

    var token = getCsrfToken();
    var formData = new FormData();
    formData.append('text', text);
    formData.append('csrfmiddlewaretoken', token);

    textarea.value = '';

    fetch('/chat/' + tripId + '/messages/', {
      method: 'POST',
      headers: {
        'Accept': 'application/json',
        'X-Requested-With': 'XMLHttpRequest',
        'X-CSRFToken': token,
      },
      body: formData,
    })
      .then(function (res) {
        return res.json().then(function (data) {
          if (!res.ok) {
            throw new Error(data.error || 'Failed to deliver message.');
          }
          return data;
        });
      })
      .then(function (data) {
        hideError();
        renderMessage(data);
      })
      .catch(function (err) {
        // Restore message on failure and notify user
        textarea.value = text;
        showError(err.message || 'Could not send message. Please check your connection.');
      })
      .finally(function () {
        isSending = false;
        if (submitBtn) {
          submitBtn.disabled = false;
          submitBtn.style.opacity = '1';
        }
        textarea.focus();
      });
  });

  // Enter sends, Shift+Enter makes new line
  if (textarea) {
    textarea.addEventListener('keydown', function (event) {
      if (event.key === 'Enter' && !event.shiftKey) {
        event.preventDefault();
        if (typeof form.requestSubmit === 'function') {
          form.requestSubmit();
        } else if (submitBtn) {
          submitBtn.click();
        }
      }
    });
  }
})();
