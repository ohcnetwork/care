/* Project specific Javascript goes here. */

// Use JS to Style all inputs with the same Tailwind classes
let inputElements = document.querySelectorAll("input");
let selectElements = document.querySelectorAll("select");
let textareaElements = document.querySelectorAll("textarea");

for (let i = 0; i < inputElements.length; i++) {
    defaultElementStyle(inputElements[i]);
    inputElements[i].classList.add("form-input");
}

for (let i = 0; i < selectElements.length; i++) {
    defaultElementStyle(selectElements[i]);
    selectElements[i].classList.add("form-select");
}

for (let i = 0; i < textareaElements.length; i++) {
    defaultElementStyle(textareaElements[i]);
    textareaElements[i].classList.add("form-input");
}

function defaultElementStyle(elem) {
    elem.classList.add("w-full");
    elem.classList.add("block");
    elem.classList.add("my-1");
}
