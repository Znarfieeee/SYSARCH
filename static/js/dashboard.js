const edit = document.getElementById('edit-btn');
const close = document.getElementById('close-btn');
const actionbtn = document.getElementById('action-btn');
const accInfo = document.getElementById('account-info');
const modal = document.getElementById('editModal');
const modalContent = document.getElementById('modalContent');

document.getElementById('edit-btn').addEventListener('click', function (event) {

    modal.classList.remove('hidden');
    setTimeout(() => {
        modalContent.classList.remove('scale-75', 'opacity-0');
        modalContent.classList.add('scale-100', 'opacity-100');
    }, 50);
}); 

//close Modal
function closeModal() {
    modalContent.classList.remove('scale-100', 'opacity-100');
    modalContent.classList.add('scale-75', 'opacity-0');
    setTimeout(() => {
        modal.classList.add('hidden');
    }, 300);
}

function previewImage(event) {
    const reader = new FileReader();
    reader.onload = function() {
        const output = document.getElementById('userPhotoPreview');
        output.src = reader.result;
    }
    reader.readAsDataURL(event.target.files[0]);
}

// for Account Info Modal
const accModal = document.getElementById('acc-modal',).addEventListener('click', function() {
    this.classList.toggle('scale-170'); // Tailwind's 125% scale class
    this.classList.toggle('z-50'); // Bring to front
    this.classList.toggle('w-full');
    this.classList.toggle('h-full'); // Adjust height if needed
    this.classList.toggle('translate-x-30')
    this.classList.toggle('translate-y-10')

    accInfo.classList.toggle('bg-white');
    accInfo.classList.toggle('bg-white/30');
    accInfo.classList.toggle('p-5');
    accInfo.classList.toggle('p-8');
    accInfo.classList.toggle('backdrop-blur-sm');
    
    edit.classList.toggle('cursor-pointer');
    edit.classList.toggle('opacity-0');

    event.stopPropagation();
});


// for Lab Rules Modal
const labModal = document.getElementById('lab-modal').addEventListener('click', function() {
    const labInfo = document.getElementById('lab-info');
    const labCont = document.getElementById('lab-content');

    this.classList.toggle('scale-150');
    this.classList.toggle('z-50');
    this.classList.toggle('w-full');
    this.classList.toggle('h-full');
    this.classList.toggle('translate-x-40')
    this.classList.toggle('translate-y-[-120px]')
    
    labInfo.classList.toggle('bg-white');
    labInfo.classList.toggle('bg-white/20');
    labInfo.classList.toggle('backdrop-blur-sm');
    
    
    // Scroll behavior
    const notExpanded = labInfo.classList.contains('overflow-hidden');
    
    if (notExpanded) {
        labInfo.classList.remove('overflow-hidden', 'h-[320px]');
        labInfo.classList.add('overflow-y-auto', 'h-[430px]');
    }else{
        labInfo.scrollTo({top: 0, behavior: 'smooth'});

        setTimeout(() => {
            labInfo.classList.remove('overflow-y-auto', 'h-[430px]');
            labInfo.classList.add('overflow-hidden', 'h-[320px]');
        })
    }
    
    event.stopPropagation();
});