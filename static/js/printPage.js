function dimPage(){
    let height = document.body.scrollHeight;
    let overlay = document.createElement('div');
    overlay.style.cssText = 'position:absolute;width:100%;height:100%;opacity:0.4;z-index:100;background:#000;top:0;left:0';
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