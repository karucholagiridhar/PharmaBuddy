document.addEventListener('DOMContentLoaded', function() {
    
    // Time Field Management
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
        wrapper.className = 'input-group mb-2 time-entry';
        
        const input = document.createElement('input');
        input.type = 'time';
        input.name = 'times';
        input.className = 'form-control';
        input.required = true;
        input.value = value;
        // Step 60 for 1 minute precision (default in most browsers, but explicit is good)
        input.step = '60'; 
        
        const removeBtn = document.createElement('button');
        removeBtn.type = 'button';
        removeBtn.className = 'btn btn-outline-danger';
        removeBtn.innerHTML = '<i data-feather="trash-2"></i>';
        removeBtn.onclick = function() {
            if (container.querySelectorAll('.time-entry').length > 1) {
                wrapper.remove();
            } else {
                // Clear value if it's the last one
                input.value = '';
            }
        };
        
        wrapper.appendChild(input);
        wrapper.appendChild(removeBtn);
        container.appendChild(wrapper);
        feather.replace();
    }
    
    // Client-side Form Validation
    const form = document.getElementById('medication-form');
    if (form) {
        form.addEventListener('submit', function(e) {
            if (!form.checkValidity()) {
                e.preventDefault();
                e.stopPropagation();
            }
            
            // Custom check: Ensure at least one time is set
            const times = document.getElementsByName('times');
            let hasTime = false;
            times.forEach(t => {
                if(t.value) hasTime = true;
            });
            
            if(!hasTime) {
                e.preventDefault();
                alert('Please select at least one dosage time.');
            }
            
            form.classList.add('was-validated');
        });
    }

    // Toggle Email Field
    const emailCheck = document.getElementById('email_notification');
    const emailField = document.getElementById('notification_email_container');
    const emailInput = document.getElementById('notification_email');

    if (emailCheck && emailField) {
        emailCheck.addEventListener('change', function() {
            toggleEmailField(this.checked);
        });
        // Init state
        toggleEmailField(emailCheck.checked);
    }

    function toggleEmailField(checked) {
        if (checked) {
            emailField.style.display = 'block';
            emailInput.setAttribute('required', 'required');
        } else {
            emailField.style.display = 'none';
            emailInput.removeAttribute('required');
        }
    }

});
