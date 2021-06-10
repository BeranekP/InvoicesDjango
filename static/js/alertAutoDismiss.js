let alerts = document.querySelectorAll('.alert')
for (alert of alerts){
    var bsAlert = new bootstrap.Alert(alert)
    window.setTimeout(() => bsAlert.close(), 2000)
   }