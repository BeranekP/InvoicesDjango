function dimPage(){
    let height = document.body.scrollHeight;
    let overlay = document.createElement('div');
    overlay.style.cssText = 'position:absolute;width:100%;height:100%;opacity:0.75;z-index:1000;background:#000;top:0;left:0; display:flex; align-items:center; justify-content:center;';
    overlay.innerHTML = '<img src="/static/ico/loader.svg" alt="spinner" style="z-index:5000;">'
    document.body.appendChild(overlay);

  }

  function printPage(val, type, id=''){
    sign = document.getElementById('sign')
    dimPage()
    if (id){
        window.location='/invoices/print/'+ id + '/?sign='+ val + '&asset=' + type
    }else{
        window.location='/print/?sign='+ val + '&asset='+ type
    }
  }