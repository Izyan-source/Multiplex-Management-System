/* Small, optional accessibility improvements. Forms still work without JavaScript. */
const errorSummary = document.querySelector('[data-error-summary]');

// Keep existing help text connected to its input for screen readers.
document.querySelectorAll('input[id], select[id]').forEach((field) => {
    if (field.type === 'hidden') return;
    const describedBy = new Set((field.getAttribute('aria-describedby') || '').split(' ').filter(Boolean));
    field.parentElement.querySelectorAll('.form-text').forEach((help, index) => {
        if (!help.id) help.id = `${field.id}-help-${index}`;
        describedBy.add(help.id);
    });
    if (describedBy.size) field.setAttribute('aria-describedby', [...describedBy].join(' '));

    // Show the browser's validation explanation beside the field as well.
    // Required, min/max, pattern and server validation remain unchanged.
    function showFieldError() {
        if (!field.willValidate) return;
        let message = document.getElementById(`${field.id}-error`);
        const invalid = !field.validity.valid;
        if (!message && invalid) {
            message = document.createElement('div');
            message.id = `${field.id}-error`;
            message.className = 'field-error';
            field.insertAdjacentElement('afterend', message);
            const descriptions = new Set((field.getAttribute('aria-describedby') || '').split(' ').filter(Boolean));
            descriptions.add(message.id);
            field.setAttribute('aria-describedby', [...descriptions].join(' '));
        }
        field.classList.toggle('is-invalid', invalid);
        if (invalid) field.setAttribute('aria-invalid', 'true');
        else field.removeAttribute('aria-invalid');
        if (message) {
            message.textContent = invalid ? field.validationMessage : '';
            message.hidden = !invalid;
        }
    }
    field.addEventListener('invalid', showFieldError);
    // Do not show errors while users first fill out an untouched form.
    ['input', 'change'].forEach((eventName) => field.addEventListener(eventName, () => {
        if (field.hasAttribute('aria-invalid') || document.getElementById(`${field.id}-error`)) showFieldError();
    }));
    if (errorSummary && !field.validity.valid) showFieldError();
});

// A returned error is the next useful place to read; no values are changed.
if (errorSummary) errorSummary.focus();

// Keep table guidance visible only when horizontal scrolling is necessary.
function updateTableHelp() {
    document.querySelectorAll('.table-responsive').forEach((region) => {
        const help = document.getElementById(region.getAttribute('aria-describedby'));
        if (help) help.hidden = region.scrollWidth <= region.clientWidth;
    });
}
updateTableHelp();
window.addEventListener('resize', updateTableHelp);
