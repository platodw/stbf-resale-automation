function showToast(msg, duration, type) {
    duration = duration || 2500;
    type = type || '';
    var t = document.createElement('div');
    t.className = 'toast' + (type ? ' toast-' + type : '');
    t.textContent = msg;
    document.body.appendChild(t);
    setTimeout(function() {
        t.style.transition = 'opacity 0.3s';
        t.style.opacity = '0';
        setTimeout(function() { t.remove(); }, 300);
    }, duration);
}

function showModal(opts) {
    // opts: { icon, title, message, confirmText, cancelText, onConfirm, onCancel, type }
    var overlay = document.createElement('div');
    overlay.className = 'modal-overlay';

    var box = document.createElement('div');
    box.className = 'modal-box';

    if (opts.icon) {
        var icon = document.createElement('div');
        icon.className = 'modal-icon';
        icon.textContent = opts.icon;
        box.appendChild(icon);
    }

    if (opts.title) {
        var title = document.createElement('div');
        title.className = 'modal-title';
        title.textContent = opts.title;
        box.appendChild(title);
    }

    if (opts.message) {
        var msg = document.createElement('div');
        msg.className = 'modal-message';
        msg.innerHTML = opts.message;
        box.appendChild(msg);
    }

    var actions = document.createElement('div');
    actions.className = 'modal-actions';

    if (opts.cancelText !== false) {
        var cancelBtn = document.createElement('button');
        cancelBtn.className = 'btn btn-secondary';
        cancelBtn.textContent = opts.cancelText || 'Cancel';
        cancelBtn.onclick = function() {
            overlay.remove();
            if (opts.onCancel) opts.onCancel();
        };
        actions.appendChild(cancelBtn);
    }

    var confirmBtn = document.createElement('button');
    var btnClass = 'btn-primary';
    if (opts.type === 'danger') btnClass = 'btn-danger';
    if (opts.type === 'success') btnClass = 'btn-success';
    confirmBtn.className = 'btn ' + btnClass;
    confirmBtn.textContent = opts.confirmText || 'OK';
    confirmBtn.onclick = function() {
        overlay.remove();
        if (opts.onConfirm) opts.onConfirm();
    };
    actions.appendChild(confirmBtn);

    box.appendChild(actions);
    overlay.appendChild(box);

    // Close on overlay click
    overlay.addEventListener('click', function(e) {
        if (e.target === overlay) {
            overlay.remove();
            if (opts.onCancel) opts.onCancel();
        }
    });

    // Close on Escape
    var escHandler = function(e) {
        if (e.key === 'Escape') {
            overlay.remove();
            document.removeEventListener('keydown', escHandler);
            if (opts.onCancel) opts.onCancel();
        }
    };
    document.addEventListener('keydown', escHandler);

    document.body.appendChild(overlay);
    confirmBtn.focus();
    return overlay;
}

// Alert replacement
function showAlert(icon, title, message, type) {
    showModal({
        icon: icon,
        title: title,
        message: message,
        confirmText: 'OK',
        cancelText: false,
        type: type || 'primary'
    });
}

// Confirm replacement
function showConfirm(opts) {
    showModal(opts);
}
