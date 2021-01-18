function getPreview(target, preview) {
  thumb = document.getElementById(preview);
  imgInput = document.getElementById(target);
  thumb.src = window.URL.createObjectURL(imgInput.files[0]);
  imgInput.labels[0].innerHTML = imgInput.files[0].name;
}
