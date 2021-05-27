const url = pdfUrl;


let pdfDoc = null,
  pageNum = 1,
  pageIsRendering = false,
  pageNumIsPending = null;

const scale = 1.6,
  canvas = document.querySelector('#pdf'),
  ctx = canvas.getContext('2d');

// Render the page
const renderPage = num => {
  pageIsRendering = true;

  // Get page
  pdfDoc.getPage(num).then(page => {
    // Set scale
    const viewport = page.getViewport({ scale });
    canvas.height = viewport.height;
    canvas.width = viewport.width;

    const renderCtx = {
      canvasContext: ctx,
      viewport
    };

    page.render(renderCtx).promise.then(() => {
      pageIsRendering = false;

      if (pageNumIsPending !== null) {
        renderPage(pageNumIsPending);
        pageNumIsPending = null;
      }
    });

  });
};

// Check for pages rendering
const queueRenderPage = num => {
  if (pageIsRendering) {
    pageNumIsPending = num;
  } else {
    renderPage(num);
  }
};


// Get Document
pdfjsLib
  .getDocument({data:url})
  .promise.then(pdfDoc_ => {
    pdfDoc = pdfDoc_;

    renderPage(pageNum);
    let download = document.querySelector("#download-pdf")
    download.setAttribute("href", `data:application/pdf;base64,${btoa(url)}`);
    download.setAttribute("download", fileName);
    let mail = document.querySelector("#own-mail")
    let mailForm = document.querySelector('#own-mail-form')
    mail.addEventListener('click',()=>{
      mailForm.submit()
    })
  })
  .catch(err => {
   console.log(err)
  });
