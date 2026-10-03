      #owly-widget-input{display:flex;border-top:1px solid #E2E8F0;padding:12px}\n\
      #owly-widget-input input{flex:1;border:1px solid #E2E8F0;border-radius:8px;padding:10px 14px;font-size:14px;outline:none}\n\
      #owly-widget-input input:focus{border-color:" + config.color + "}\n\
      #owly-widget-input button{background:" + config.color + ";color:#fff;border:none;border-radius:8px;padding:10px 16px;margin-left:8px;cursor:pointer;font-size:14px}\n\
    ";
    document.head.appendChild(style);
  }

  function createWidget() {
    var container = document.createElement("div");
    container.id = "owly-widget-container";
    container.innerHTML = '\
      <div id="owly-widget-panel">\
        <div id="owly-widget-header">\
          <h3>' + config.title + '</h3>\
          <button id="owly-widget-close">&times;</button>\
        </div>\
        <div id="owly-widget-messages"></div>\
        <div id="owly-widget-input">\
          <input type="text" placeholder="Type a message..." id="owly-widget-text" />\
          <button id="owly-widget-send">Send</button>\
        </div>\
      </div>\
      <button id="owly-widget-btn">\
        <svg viewBox="0 0 24 24"><path d="M20 2H4c-1.1 0-2 .9-2 2v18l4-4h14c1.1 0 2-.9 2-2V4c0-1.1-.9-2-2-2zm0 14H6l-2 2V4h16v12z"/></svg>\
      </button>\
    ';
    document.body.appendChild(container);

    document.getElementById("owly-widget-btn").onclick = toggleWidget;
    document.getElementById("owly-widget-close").onclick = toggleWidget;
