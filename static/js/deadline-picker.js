document.addEventListener('DOMContentLoaded', () => {
    document.querySelectorAll('.deadline-picker').forEach((input) => {
        if (!window.flatpickr) {
            input.type = 'datetime-local';
            input.placeholder = '';
            return;
        }

        flatpickr(input, {
            enableTime: true,
            time_24hr: true,
            dateFormat: 'Y-m-d\\TH:i',
            altInput: true,
            altFormat: 'Y年n月j日（D） H:i',
            locale: 'ja',
            disableMobile: true,
        });
    });
});
