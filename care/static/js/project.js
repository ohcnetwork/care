/* Project specific Javascript goes here. */

// Use JS to Style all inputs with the same Tailwind classes
let inputElements = document.querySelectorAll('input');
let selectElements = document.querySelectorAll('select');

for (let i = 0; i < inputElements.length; i++) {
    defaultElementStyle(inputElements[i]);
    inputElements[i].classList.add('form-input');
}

for (let i = 0; i < selectElements.length; i++) {
    defaultElementStyle(selectElements[i]);
    selectElements[i].classList.add('form-select');
}

function defaultElementStyle(elem) {
    elem.classList.add("w-full");
    elem.classList.add("block");
    elem.classList.add("my-1");
}
