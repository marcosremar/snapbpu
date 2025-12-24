import React from 'react'

/**
 * 14-Bis - Avião do Santos Dumont como background decorativo
 */
export default function Plane14Bis({ className = '' }) {
  return (
    <div className={`plane-14bis-container ${className}`}>
      {/* Avião principal - direita */}
      <svg 
        className="plane-14bis plane-1" 
        viewBox="0 0 400 200" 
        fill="none" 
        xmlns="http://www.w3.org/2000/svg"
      >
        <g stroke="#10b981" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round" opacity="0.4">
          {/* Fuselagem central */}
          <path d="M50 100 H320" />
          
          {/* Asa superior */}
          <path d="M100 100 V55 H280 V100" />
          <path d="M110 55 V35 H270 V55" />
          
          {/* Asa inferior */}
          <path d="M100 100 V145 H280 V100" />
          
          {/* Montantes verticais */}
          <path d="M130 35 V145" />
          <path d="M170 35 V145" />
          <path d="M210 35 V145" />
          <path d="M250 35 V145" />
          
          {/* Cabos diagonais superiores */}
          <path d="M130 35 L150 55" />
          <path d="M170 35 L190 55" />
          <path d="M210 35 L190 55" />
          <path d="M250 35 L230 55" />
          
          {/* Cabos diagonais inferiores */}
          <path d="M130 145 L150 125" />
          <path d="M250 145 L230 125" />
          
          {/* Canard (leme frontal) - característica única do 14-bis */}
          <path d="M320 100 H360" />
          <rect x="340" y="85" width="35" height="30" rx="3" />
          
          {/* Cauda */}
          <path d="M50 100 H30" />
          <path d="M30 75 V125" />
          <path d="M15 85 L30 100 L15 115" />
          
          {/* Hélice */}
          <ellipse cx="385" cy="100" rx="5" ry="25" />
          
          {/* Rodas */}
          <circle cx="145" cy="160" r="12" />
          <circle cx="235" cy="160" r="12" />
          <path d="M145 172 H235" />
        </g>
      </svg>

      {/* Avião secundário - esquerda (menor) */}
      <svg 
        className="plane-14bis plane-2" 
        viewBox="0 0 400 200" 
        fill="none" 
        xmlns="http://www.w3.org/2000/svg"
      >
        <g stroke="#8b5cf6" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round" opacity="0.25">
          <path d="M50 100 H320" />
          <path d="M100 100 V55 H280 V100" />
          <path d="M110 55 V35 H270 V55" />
          <path d="M100 100 V145 H280 V100" />
          <path d="M130 35 V145" />
          <path d="M170 35 V145" />
          <path d="M210 35 V145" />
          <path d="M250 35 V145" />
          <path d="M320 100 H360" />
          <rect x="340" y="85" width="35" height="30" rx="3" />
          <path d="M50 100 H30" />
          <path d="M30 75 V125" />
          <path d="M15 85 L30 100 L15 115" />
          <ellipse cx="385" cy="100" rx="5" ry="25" />
          <circle cx="145" cy="160" r="12" />
          <circle cx="235" cy="160" r="12" />
        </g>
      </svg>

      <style>{`
        .plane-14bis-container {
          position: absolute;
          inset: 0;
          overflow: hidden;
          pointer-events: none;
          z-index: 1;
        }
        
        .plane-14bis {
          position: absolute;
        }
        
        .plane-14bis.plane-1 {
          width: 450px;
          height: 270px;
          top: 8%;
          right: 3%;
          animation: fly1 20s ease-in-out infinite;
        }
        
        .plane-14bis.plane-2 {
          width: 280px;
          height: 168px;
          bottom: 15%;
          left: 5%;
          animation: fly2 25s ease-in-out infinite;
        }
        
        @keyframes fly1 {
          0%, 100% {
            transform: translate(0, 0) rotate(-2deg);
          }
          25% {
            transform: translate(30px, -15px) rotate(0deg);
          }
          50% {
            transform: translate(50px, 5px) rotate(-1deg);
          }
          75% {
            transform: translate(20px, -20px) rotate(-3deg);
          }
        }
        
        @keyframes fly2 {
          0%, 100% {
            transform: translate(0, 0) rotate(1deg);
          }
          33% {
            transform: translate(-20px, -10px) rotate(-1deg);
          }
          66% {
            transform: translate(15px, 8px) rotate(2deg);
          }
        }
      `}</style>
    </div>
  )
}
