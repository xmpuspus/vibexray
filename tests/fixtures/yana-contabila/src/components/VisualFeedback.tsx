      },
    });
  }
}

// Animation helpers
export const createSuccessAnimation = () => {
  const confetti = document.createElement('div');
  confetti.className = 'fixed inset-0 pointer-events-none z-[9999]';
  confetti.innerHTML = `
    <div class="absolute inset-0 flex items-center justify-center">
      <div class="animate-ping absolute h-32 w-32 rounded-full bg-green-500/20"></div>
      <div class="animate-pulse absolute h-24 w-24 rounded-full bg-green-500/30"></div>
    </div>
  `;
  document.body.appendChild(confetti);
  setTimeout(() => confetti.remove(), 1000);
};

export const createErrorAnimation = () => {
  const shake = document.createElement('style');
