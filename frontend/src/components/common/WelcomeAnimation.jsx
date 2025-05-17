import React, { useState, useEffect } from 'react';

const WelcomeAnimation = () => {
  const [animationStep, setAnimationStep] = useState(0);
  const [fadeState, setFadeState] = useState('in');
  const [wordToChange, setWordToChange] = useState('data');
  const [restartAnimation, setRestartAnimation] = useState(false);

  // Animation sequence:
  // 0: "From data" slides up
  // 1: "to graphs" slides in from right
  // 2: "graphs" fades to "signals"
  // 3: "signals" fades to "trade"
  // 4: "ETHSight is here for you" slides up
  
  useEffect(() => {
    if (animationStep >= 5) {
      // Restart animation after a delay
      const restartTimer = setTimeout(() => {
        setRestartAnimation(true);
        setAnimationStep(0);
        setFadeState('in');
        setWordToChange('data');
        setTimeout(() => setRestartAnimation(false), 100);
      }, 0);
      return () => clearTimeout(restartTimer);
    }

    const timer = setTimeout(() => {
      if (fadeState === 'in') {
        setFadeState('out');
      setTimeout(() => {
          switch (animationStep) {
            case 0: // Move to step 1
              setWordToChange('graphs');
              setAnimationStep(1);
              setFadeState('in');
              break;
            case 1: // Move to step 2
              setWordToChange('signals');
              setFadeState('in');
              setAnimationStep(2);
              break;
            case 2: // Move to step 3
              setWordToChange('trade');
              setFadeState('in');
              setAnimationStep(3);
              break;
            case 3: // Move to step 4
              setAnimationStep(4);
              setFadeState('in');
              break;
            case 4: // End of animation
              setAnimationStep(5);
              break;
          }
        }, 250); // Half a second for transitions
      }
    }, animationStep === 0 || animationStep === 4 ? 2000 : 1500);
    
    return () => clearTimeout(timer);
  }, [animationStep, fadeState]);

  if (restartAnimation) {
    return <div className="h-52"></div>;
  }
  
  return (
    <div className="flex flex-col items-center justify-center h-full">
      <div className="text-center relative h-52 overflow-hidden w-full max-w-md -mt-20">
        {/* From data */}
        {animationStep === 0 && (
          <div 
            className="text-3xl md:text-4xl lg:text-5xl font-bold absolute inset-x-0 transition-all duration-700 ease-out"
            style={{ 
              top: '50%',
              transform: `translate3d(0, ${fadeState === 'in' ? '-50%' : '-150%'}, 0)`,
              opacity: fadeState === 'in' ? 1 : 0
            }}
          >
            <span className="text-gray-800">From </span>
            <span className="text-primary-main">data</span>
          </div>
        )}
        
        {/* to signals/trade */}
        {(animationStep === 1 || animationStep === 2 || animationStep === 3) && (
          <div 
            className="text-3xl md:text-4xl lg:text-5xl font-bold absolute inset-x-0 transition-all duration-500"
            style={{ 
              top: '50%',
              transform: 'translate3d(0, -50%, 0)',
            }}
          >
            <span className="text-gray-800">to </span>
          <span 
              className="text-primary-main inline-block transition-all duration-500"
              style={{
                opacity: fadeState === 'in' ? 1 : 0,
                transform: fadeState === 'in' ? 'scale(1)' : 'scale(0.8)',
                filter: fadeState === 'in' ? 'blur(0)' : 'blur(4px)'
              }}
            >
              {wordToChange}
            </span>
          </div>
        )}
        
        {/* ETHSight is here for you */}
        {animationStep === 4 && (
          <div 
            className="absolute inset-x-0 transition-all duration-700 ease-out"
            style={{ 
              top: '50%',
              transform: `translate3d(0, ${fadeState === 'in' ? '-50%' : '50%'}, 0)`,
              opacity: fadeState === 'in' ? 1 : 0
            }}
          >
            <div className="text-3xl md:text-4xl lg:text-5xl font-bold">
              <span className="text-primary-main">ETHSight</span>
              <br />
              <span className="text-gray-800"> is here for you</span>
            </div>
          </div>
        )}
      </div>
    </div>
  );
};

export default WelcomeAnimation; 