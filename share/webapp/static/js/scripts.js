
function showTab(tabIndex) {
  var tabs = document.getElementsByClassName('tab');
  var buttons = document.getElementsByClassName('tab-button');

  for (var i = 0; i < tabs.length; i++) {
    tabs[i].classList.remove('active');
    buttons[i].classList.remove('active');
  }

  tabs[tabIndex].classList.add('active');
  buttons[tabIndex].classList.add('active');
}

function register_svg(cid) {
  svg_el = document.querySelector("#" + cid + " svg");
  if (svg_el != null) {
    console.log("(register_svg) found " + cid);
    svgPanZoom(svg_el, {controlIconsEnabled: true, zoomScaleSensitivity: 0.4, minZoom: 0.01, maxZoom: 1000.});
  } else {
    console.log("(register_svg) missing " + cid);
  }
}


function register_collapsibles() {
  var collapsibles = document.querySelectorAll('.collapsible');

  collapsibles.forEach(function(collapsible) {
    var heading = collapsible.querySelector('h3');
    var content = collapsible.querySelector('.content');

    heading.addEventListener('click', function() {
      collapsible.classList.toggle('active');

      if (content.style.display === 'block') {
        content.style.display = 'none';
      } else {
        content.style.display = 'block';
      }
    });
  });
}
