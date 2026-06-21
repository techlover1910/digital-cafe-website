const tools = [
  {
    title: 'AI Passport Photo Maker',
    description: 'Background remove, auto crop, aur 6/12 grid print ready output.'
  },
  {
    title: 'PVC ID Cropper',
    description: 'Aadhaar ya anya ID ki PDF se both sides ko correct size mein cut karna.'
  },
  {
    title: 'Pan / Form Resizer',
    description: 'NSDL/UTI ke requirements ke hisaab se photo aur signature auto set.'
  },
  {
    title: 'PDF Converter Pro',
    description: 'PDF se JPG aur JPG se PDF conversion bina kisi external website ke.'
  },
  {
    title: 'PDF Toolbox',
    description: 'Merge multiple files aur compress size as per portal limits.'
  },
  {
    title: 'Government Form Resizer',
    description: 'Photo aur signature ko 20KB, 50KB jaise presets mein fix karna.'
  },
  {
    title: 'Photo-Sign Merge',
    description: 'Bank ya exam form ke liye photo aur sign ko ek file mein align karna.'
  },
  {
    title: 'Digital Signature Cleaner',
    description: 'Shadow remove karke signature ko pure black & white mein convert karna.'
  },
  {
    title: 'Café Receipt Generator',
    description: 'Customer details, services aur prices ke saath receipt generate aur print.'
  }
];

const toolGrid = document.getElementById('tool-grid');

tools.forEach((tool) => {
  const card = document.createElement('article');
  card.className = 'tool-card';
  card.innerHTML = `
    <h3>${tool.title}</h3>
    <p>${tool.description}</p>
  `;
  toolGrid.appendChild(card);
});
