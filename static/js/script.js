function getCSRFToken() {
    return document.querySelector(
        'input[name="csrf_token"]'
    )?.value;
}

console.log("Feed JS Loaded");

document.addEventListener("click", async function(e){

if(e.target.closest(".like-btn")){

let btn=e.target.closest(".like-btn");
let postId=btn.dataset.postId;

let res=await fetch(`/like/${postId}`,{
    method:"POST",
    headers:{
        "X-CSRFToken": getCSRFToken()
    }
});

let data=await res.json();

document.getElementById(
`like-count-${postId}`
).innerText=data.likes;
}

if (e.target.closest(".share-btn")) {

    let btn = e.target.closest(".share-btn");
    let postId = btn.dataset.postId;

    let shareUrl = window.location.origin + `/post/${postId}`;

    // Copy link
    let textarea = document.createElement("textarea");
    textarea.value = shareUrl;
    document.body.appendChild(textarea);

    textarea.select();
    document.execCommand("copy");

    textarea.remove();

    // Increase share count
    let res = await fetch(`/share/${postId}`, {
    method: "POST",
    headers:{
        "X-CSRFToken": getCSRFToken()
    }
});

    let data = await res.json();

    document.getElementById(
        `share-count-${postId}`
    ).innerText = data.shares;

    alert("🔗 Link copied! You can share it anywhere.");
}

if(e.target.closest(".toggle-comment")){

let postId=
e.target.closest(".toggle-comment").dataset.postId;

let box=document.getElementById(
`comments-${postId}`
);

box.style.display=
(box.style.display==="block")
? "none":"block";
}

if(e.target.closest(".comment-submit")){

let btn=e.target.closest(".comment-submit");

if(btn.disabled) return;
btn.disabled=true;

let postId=btn.dataset.postId;
let input=document.getElementById(
`comment-input-${postId}`
);
let content=input.value.trim();

if(!content){
btn.disabled=false;
return;
}

let res=await fetch(`/comment/${postId}`,{
    method:"POST",
    headers:{
        "Content-Type":"application/x-www-form-urlencoded",
        "X-CSRFToken": getCSRFToken()
    },
    body:`content=${encodeURIComponent(content)}`
});

let data=await res.json();

if(data.status==="ok"){
let list=document.querySelector(
`#comments-${postId} .comments-list`
);

let div=document.createElement("div");
div.innerHTML=
`<strong>You</strong>: ${content}`;

list.appendChild(div);

input.value="";
}
btn.disabled=false;
}

if(e.target.closest(".delete-comment")){

    let btn = e.target.closest(".delete-comment");
    let commentId = btn.dataset.commentId;

    let res = await fetch(`/delete_comment/${commentId}`, {
    method: "POST",
    headers:{
        "X-CSRFToken": getCSRFToken()
    }
});
    
    let data = await res.json();

    if(data.status === "ok"){
        btn.closest(".comment-item").remove();
    } else {
        alert("You can only delete your own comment.");
    }
}
if(e.target.closest(".delete-btn")){

let btn = e.target.closest(".delete-btn");
let postId = btn.dataset.postId;

let res = await fetch(`/delete_post/${postId}`,{
    method:"POST",
    headers:{
        "X-CSRFToken": getCSRFToken()
    }
});

let data = await res.json();
if(data.status === "ok"){
document.getElementById(
`post-${postId}`
).remove();

}
}
});
