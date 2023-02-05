function downloadCreated(download) {
    var newd = {      'id': download.id,
                     'filename': download.filename,
                     'state': 'started',
                     'start_time': download.startTime,
                     'url': download.url,
                     "mime": download.mime,
                    "typ": "new_download"
    };
    sendf_msg_via_http(newd)
    console.log("New download "+JSON.stringify(newd));
}

function handleChanged(delta) {
  if (delta.state && delta.state.current === "complete") {
      sendf_msg_via_http({'typ': 'download_state_complete', "id": delta.id})
  }
    if (delta.state && delta.state.current === "interrupted") {
        sendf_msg_via_http({'typ': 'download_state_interrupted', "id": delta.id})
    }}

chrome.downloads.onChanged.addListener(handleChanged);
chrome.downloads.onCreated.addListener(downloadCreated);

////////////

function addTardisHeader(e){
    var value = e.requestId+" " +e.tabId +  " " +e.parentFrameId + " " + e.frameId + " " + e.initiator + " " + e.type +" " + e.timeStamp;
    var new_header = {"name": "tardis_header","value":value};
    console.log({"name": "tardis_header","value":value});
    e.requestHeaders.push(new_header);
    return {requestHeaders: e.requestHeaders};
}

function before_request(requestDetails) {

    if (is_msg_from_master(requestDetails.url)){
        do_command(requestDetails.url);
        return {cancel: true};
    }
    if (!is_msg_for_master(requestDetails.url)){

        new_request = {  "typ": "before_request",
                "url": requestDetails.url,
                "timestamp": requestDetails.timeStamp,
                "frame_id": requestDetails.frameId,
                'parent_frame': requestDetails.parentFrameId,
                "request_id": requestDetails.requestId,
                "tab_id": requestDetails.tabId,
                "originUrl": requestDetails.originUrl,
                "type": requestDetails.type,
                "initiator": requestDetails.initiator}

        console.log("type: " + requestDetails.initiator)
        requestDetails.url = requestDetails.url + '&katti_request_id=' + requestDetails.requestId
        console.log(requestDetails.url)
        sendf_msg_via_http(new_request)
     }

}

function start_request(requestDetails){
    if (!is_msg_from_master(requestDetails.url) && !is_msg_for_master(requestDetails.url)){
        sendf_msg_via_http(
        {
            "typ": "start_response",
            "timestamp": requestDetails.timeStamp,
            "request_id": requestDetails.requestId,
            "frame_id": requestDetails.frameId
        });
    }
}


function before_navigate(nav){
    if (!is_msg_from_master(nav.url) && !is_msg_for_master(nav.url)){
        sendf_msg_via_http(
        {
            "typ": "before_navigate",
            "timestamp": nav.timeStamp,
            "nav_url": nav.url,
            'tab_id': nav.tabId,
            'frame_id': nav.frameId,
            'parent_frame': nav.parentFrameId
        });
    }

}


function new_tab(tab){
    sendf_msg_via_http({
        "typ": "new_tab",
        "window_id": tab.windowId,
        "tab_id": tab.id,
        "url": tab.url,
        "title": tab.title,
        "timestamp":new Date().getTime()
    });
}

function new_window(window){
        sendf_msg_via_http({
        "typ": "new_window",
        "window_id": window.id,
        "window_type": window.type,
        "timestamp":new Date().getTime()
    });
}

function before_redirect(redi){
    sendf_msg_via_http(
        {
            "typ": "before_redirect",
            "old_url": redi.url,
            "redirect_url": redi.redirectUrl,
            "timestamp": redi.timeStamp,
            "frame_id": redi.frameId,
            "request_id": redi.requestId,
            "tab_id": redi.tabId
        });

}

function handleAlarm(alarmInfo) {
        sendf_msg_via_http({
        "typ": "new_alarm",
        "info": alarmInfo.name,
         "timestamp": new Date().getTime()
    });
  console.log("on alarm: " + alarmInfo.name);
}

function addon_installed(info) {
        var x = {
        "typ": "new_addon",
        "homepageUrl": info.homepageUrl,
        "hostPermissions": info.hostPermissions,
        "installType": info.installType,
        "name": info.name,
        "permissions": info.permissions,
        "type": info.type,
            "timestamp": new Date().getTime()
    };
       sendf_msg_via_http(x);
  console.log("addon: " + JSON.stringify(x));
}

chrome.webRequest.onBeforeRequest.addListener(
    before_request,
    {urls: ["<all_urls>"]},
     ["blocking"]
  );
  
  chrome.webRequest.onResponseStarted.addListener(
    start_request,
    {urls: ["<all_urls>"]}
  );
  
  chrome.webNavigation.onBeforeNavigate.addListener(
    before_navigate
    );

  chrome.webRequest.onBeforeRedirect.addListener(
    before_redirect,
    {urls: ["<all_urls>"]}
  );

  chrome.webRequest.onBeforeSendHeaders.addListener(
      addTardisHeader,
      {urls: ["<all_urls>"]},
      ['blocking', 'requestHeaders' , 'extraHeaders']
  );

  
  chrome.tabs.onCreated.addListener(new_tab);
  chrome.windows.onCreated.addListener(new_window);
  chrome.runtime.onMessage.addListener((message, sender, sendResponse) => {
      console.log('hallo')
      sendResponse("Response from TARTDIS:tab_id=tardis_tag="+ sender.tab.id+" frame_id=tardis_tag="+sender.frameId+" url=tardis_tag="+sender.url+" window_id=tardis_tag="+sender.tab.windowId);}
  );



  chrome.management.onInstalled.addListener(addon_installed);
  chrome.alarms.onAlarm.addListener(handleAlarm);
//Utils


function do_command(url){
    var u = new URL(url)

}



function sendf_msg_via_http(msg){
console.log(msg);
    fetch('http://127.0.0.1:8080/logs', {method: 'POST', body: JSON.stringify(msg)});
}



function is_msg_from_master(url){
    const u = new URL(url);
    return u.hostname.indexOf("hey_tardis") >= 0;
}

function is_msg_for_master(url){
    const u = new URL(url);
    return u.hostname === "127.0.0.1";
}




