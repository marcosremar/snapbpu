import React from 'react'
import DumontLogo from './DumontLogo'

/**
 * LogoIcon - Apenas o ícone da nuvem com o D
 */
export function LogoIcon({ size = 48, className = '' }) {
  return <DumontLogo size={size} className={className} />
}

/**
 * Logo - Ícone + texto "Dumont Cloud" com estilos diferentes
 *
 * @param {number} size - Tamanho do ícone (default: 48)
 * @param {string} className - Classes CSS adicionais
 */
export default function Logo({ size = 48, className = '' }) {
  return (
    <div className={`logo-container ${className}`} style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
      <DumontLogo size={size} />
      <span className="brand-name">
        <span className="brand-dumont">Dumont</span>
        <span className="brand-cloud">Cloud</span>
      </span>
    </div>
  )
}
