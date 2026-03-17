document.addEventListener('DOMContentLoaded', function() {

    // ── Time Field Management ─────────────────────────────────────
    const container = document.getElementById('times-container');
    const addButton = document.getElementById('add-time-btn');

    if (addButton && container) {
        addButton.addEventListener('click', function() {
            addTimeField();
        });

        // Add initial field if empty
        if (container.children.length === 0) {
            addTimeField();
        }
    }

    function addTimeField(value = '') {
        const wrapper = document.createElement('div');
        wrapper.className = 'time-entry';
        wrapper.style.cssText = 'display:flex;gap:8px;margin-bottom:8px;align-items:center;';

        const input = document.createElement('input');
        input.type = 'time';
        input.name = 'times';
        input.className = 'ez-input';
        input.style.flex = '1';
        input.required = true;
        input.value = value;
        input.step = '60';

        const removeBtn = document.createElement('button');
        removeBtn.type = 'button';
        removeBtn.className = 'btn-danger-ghost';
        removeBtn.style.cssText = 'padding:5px 10px;font-size:13px;flex-shrink:0;';
        removeBtn.textContent = '×';
        removeBtn.title = 'Remove time';
        removeBtn.onclick = function() {
            if (container.querySelectorAll('.time-entry').length > 1) {
                wrapper.remove();
            } else {
                input.value = '';
            }
        };

        wrapper.appendChild(input);
        wrapper.appendChild(removeBtn);
        container.appendChild(wrapper);
        input.focus();
    }

    // ── Form Validation ───────────────────────────────────────────
    const form = document.getElementById('medication-form');
    if (form) {
        form.addEventListener('submit', function(e) {
            const times = document.getElementsByName('times');
            let hasTime = false;
            times.forEach(t => { if (t.value) hasTime = true; });

            if (!hasTime) {
                e.preventDefault();
                alert('Please select at least one dosage time.');
                return;
            }

            if (!form.checkValidity()) {
                e.preventDefault();
                e.stopPropagation();
            }
            form.classList.add('was-validated');
        });
    }

});
