let mailBtn = document.getElementById('mailcopy'); 
        
mailBtn.addEventListener('change', (e)=>{
  //e.preventDefault();
  console.log(e.target.value)
  e.target.value = e.target.checked;
  console.log(e.target.value)
  document.getElementById('mailcopy-form').submit();
});
