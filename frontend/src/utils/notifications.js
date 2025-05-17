export const showTransactionNotification = (txHash) => {
  const message = document.createElement('div');
  message.className = 'fixed bottom-4 right-4 bg-primary-main text-black px-4 py-3 rounded-lg shadow-lg transition-opacity duration-500 flex items-center space-x-2 z-50';
  
  const link = document.createElement('a');
  link.href = `https://sepolia.basescan.org/tx/${txHash}`;
  link.target = '_blank';
  link.rel = 'noopener noreferrer';
  link.className = 'flex items-center hover:text-white/90';
  
  // Add checkmark icon
  const checkmark = document.createElementNS('http://www.w3.org/2000/svg', 'svg');
  checkmark.setAttribute('class', 'w-5 h-5 mr-2');
  checkmark.setAttribute('viewBox', '0 0 20 20');
  checkmark.setAttribute('fill', 'currentColor');
  const path = document.createElementNS('http://www.w3.org/2000/svg', 'path');
  path.setAttribute('fillRule', 'evenodd');
  path.setAttribute('d', 'M10 18a8 8 0 100-16 8 8 0 000 16zm3.707-9.293a1 1 0 00-1.414-1.414L9 10.586 7.707 9.293a1 1 0 00-1.414 1.414l2 2a1 1 0 001.414 0l4-4z');
  path.setAttribute('clipRule', 'evenodd');
  checkmark.appendChild(path);
  
  const text = document.createElement('span');
  text.textContent = 'Subscription successful! View transaction';
  
  // Add external link icon
  const externalLink = document.createElementNS('http://www.w3.org/2000/svg', 'svg');
  externalLink.setAttribute('class', 'w-4 h-4 ml-1');
  externalLink.setAttribute('viewBox', '0 0 20 20');
  externalLink.setAttribute('fill', 'currentColor');
  const linkPath = document.createElementNS('http://www.w3.org/2000/svg', 'path');
  linkPath.setAttribute('d', 'M11 3a1 1 0 100 2h2.586l-6.293 6.293a1 1 0 101.414 1.414L15 6.414V9a1 1 0 102 0V4a1 1 0 00-1-1h-5z');
  const linkPath2 = document.createElementNS('http://www.w3.org/2000/svg', 'path');
  linkPath2.setAttribute('d', 'M5 5a2 2 0 00-2 2v8a2 2 0 002 2h8a2 2 0 002-2v-3a1 1 0 10-2 0v3H5V7h3a1 1 0 000-2H5z');
  externalLink.appendChild(linkPath);
  externalLink.appendChild(linkPath2);
  
  link.appendChild(checkmark);
  link.appendChild(text);
  link.appendChild(externalLink);
  message.appendChild(link);
  document.body.appendChild(message);
  
  // Remove the message after 5 seconds
  setTimeout(() => {
    message.style.opacity = '0';
    setTimeout(() => document.body.removeChild(message), 500);
  }, 5000);
}; 