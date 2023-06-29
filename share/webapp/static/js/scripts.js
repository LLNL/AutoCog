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
