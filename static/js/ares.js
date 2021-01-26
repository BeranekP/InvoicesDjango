let ic = document.getElementById('icInput');
  
  async function ValidateIC(value){
    const response = await fetch(window.origin +'/checkic/?ic='+value);
    return await response.json();
  }
  ic.addEventListener('input',e=>{
    e.preventDefault();
    if (ic.value){
    ValidateIC(ic.value).then(data=>{
     if (data != 'Not found' && parseInt(data.pf.code) <= 108){
       let name = data.name.split(" ");
       if (name.length > 2){
         document.getElementById('ic-ares').innerHTML='<em>ARES: <strong> Nalezeno! </strong></em>';
         document.getElementById('inlineRadio1').click();
          let first = name[1];
          let last = name[2];
          document.getElementById('name-ares').innerHTML='<em>ARES: <strong>' + first + '</strong></em>';
          document.getElementById('surname-ares').innerHTML='<em>ARES: <strong>' + last +'</strong></em>';
          document.getElementById('street-ares').innerHTML='<em>ARES: <strong>' + data.street + ' ' + data.house_no +'</strong></em>';
          document.getElementById('town-ares').innerHTML='<em>ARES: <strong>' + data.town +'</strong></em>';
          document.getElementById('zipcode-ares').innerHTML='<em>ARES: <strong>' + data.zipcode +'</strong></em>';
          }
       else if (name.length == 2){
         document.getElementById('ic-ares').innerHTML='<em>ARES: <strong> Nalezeno! </strong></em>';
         document.getElementById('inlineRadio1').click();
        let first = name[0];
        let last = name[1];
        document.getElementById('name-ares').innerHTML='<em>ARES: <strong>' + first + '</strong></em>';
        document.getElementById('surname-ares').innerHTML='<em>ARES: <strong>' + last + '</strong></em>';
        document.getElementById('street-ares').innerHTML='<em>ARES: <strong>' + data.street + ' ' + data.house_no +'</strong></em>';
        document.getElementById('town-ares').innerHTML='<em>ARES: <strong>' + data.town +'</strong></em>';
        document.getElementById('zipcode-ares').innerHTML='<em>ARES: <strong>' + data.zipcode +'</strong></em>';
       }
     } else if (data != 'Not found' && parseInt(data.pf.code) > 108){
       document.getElementById('ic-ares').innerHTML='<em>ARES: <strong> Nalezeno! </strong></em>';
       document.getElementById('inlineRadio2').click();
       let first = '';
       let last = data.name;
       document.getElementById('surname-ares').innerHTML='<em>ARES: <strong>' + last + '</strong></em>';
        document.getElementById('street-ares').innerHTML='<em>ARES: <strong>' + data.street + ' ' + data.house_no +'</strong></em>';
        document.getElementById('town-ares').innerHTML='<em>ARES: <strong>' + data.town +'</strong></em>';
        document.getElementById('zipcode-ares').innerHTML='<em>ARES: <strong>' + data.zipcode +'</strong></em>';
     }else{
       document.getElementById('ic-ares').innerHTML='<em>ARES: <strong> Nenalezeno! </strong></em>';
       for (let el of document.getElementsByClassName('ares')){
         el.innerHTML='';
       }
     }
     
     
    }
     
    )
     }
  });