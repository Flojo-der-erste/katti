function handleResponse(response) {
  var newDiv = window.document.createElement("div");
  console.log("hallo es geht los");
  newDiv.setAttribute("style", "display: none;");
  newDiv.setAttribute("id", "tardis_tag");
  var newContent = window.document.createTextNode(response);
  newDiv.appendChild(newContent);
  window.document.body.appendChild(newDiv);
  console.log(`${response}`);}


function handleError(error) {
  console.log(`Error: ${error}`);}


function notifyBackgroundPage() {
  console.log('Ask background');
  chrome.runtime.sendMessage('Dr who?', (response) => {
      if(!response)
    console.log('message error: ', chrome.runtime.lastError.message);
    console.log(response);
    handleResponse(response);
  });}


notifyBackgroundPage();
window.onload = (event) => {
  console.log('page is fully loaded');
  var newDiv = document.createElement("div");
    newDiv.setAttribute("style", "display: none;");
    newDiv.setAttribute("id", "add_is_ready_tag");
    document.body.appendChild(newDiv);}


