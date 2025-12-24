import React from 'react'
import { ArrowRight } from 'lucide-react'

// Base: Material Green #2e7d32
// Ordenado por padrões de mercado (mais comum primeiro)
const buttonStyles = {
  // 1-5: Os mais usados no mercado (Flat/Material Design)
  1: { background: '#2e7d32' }, // Flat puro - o mais comum
  2: { background: '#2e7d32', borderRadius: '8px' }, // Flat arredondado - padrão Google/Material
  3: { background: '#2e7d32', borderRadius: '6px', boxShadow: '0 2px 4px rgba(0,0,0,0.15)' }, // Flat com sombra leve - Bootstrap style
  4: { background: '#2e7d32', borderRadius: '4px' }, // Flat quadrado - padrão corporativo
  5: { background: '#2e7d32', borderRadius: '50px' }, // Pill - muito usado em apps modernos

  // 6-10: Sombras (Material Design / Elevation)
  6: { background: '#2e7d32', boxShadow: '0 2px 4px rgba(0,0,0,0.2)' }, // Material elevation 1
  7: { background: '#2e7d32', boxShadow: '0 4px 8px rgba(0,0,0,0.2)' }, // Material elevation 2
  8: { background: '#2e7d32', boxShadow: '0 6px 12px rgba(0,0,0,0.15)' }, // Material elevation 3
  9: { background: '#2e7d32', boxShadow: '0 4px 12px rgba(46, 125, 50, 0.3)' }, // Colored shadow - tendência atual
  10: { background: '#2e7d32', boxShadow: '0 8px 20px rgba(46, 125, 50, 0.35)' }, // Strong colored shadow

  // 11-15: Gradientes (muito usado em landing pages)
  11: { background: 'linear-gradient(135deg, #43a047, #2e7d32)' }, // Gradiente diagonal - muito popular
  12: { background: 'linear-gradient(180deg, #388e3c, #2e7d32)' }, // Gradiente vertical
  13: { background: 'linear-gradient(90deg, #2e7d32, #388e3c)' }, // Gradiente horizontal
  14: { background: 'linear-gradient(135deg, #4caf50, #2e7d32)' }, // Gradiente claro
  15: { background: 'linear-gradient(135deg, #2e7d32, #1b5e20)' }, // Gradiente escuro

  // 16-20: Bordas (padrão em sistemas e dashboards)
  16: { background: '#2e7d32', border: '1px solid rgba(255,255,255,0.1)' }, // Borda sutil
  17: { background: '#2e7d32', border: '2px solid #1b5e20' }, // Borda escura
  18: { background: '#2e7d32', border: '2px solid #4caf50' }, // Borda clara
  19: { background: '#2e7d32', border: '1px solid rgba(255,255,255,0.2)', borderRadius: '8px' }, // Borda + arredondado
  20: { background: 'transparent', border: '2px solid #2e7d32', color: '#2e7d32' }, // Ghost/Outline button

  // 21-25: 3D / Neumorfismo (tendência UI)
  21: { background: '#2e7d32', boxShadow: '0 4px 0 #1b5e20' }, // 3D clássico
  22: { background: '#2e7d32', boxShadow: '0 3px 0 #1b5e20', borderRadius: '8px' }, // 3D arredondado
  23: { background: '#2e7d32', boxShadow: 'inset 0 -3px 0 rgba(0,0,0,0.2)' }, // Inset bottom
  24: { background: '#2e7d32', boxShadow: 'inset 0 1px 0 rgba(255,255,255,0.2), inset 0 -1px 0 rgba(0,0,0,0.1)' }, // Brilho interno
  25: { background: 'linear-gradient(180deg, #388e3c, #2e7d32)', boxShadow: '0 3px 0 #1b5e20' }, // 3D + gradiente

  // 26-30: SaaS / Tech (Stripe, Vercel, Linear style)
  26: { background: '#2e7d32', borderRadius: '6px', boxShadow: '0 1px 2px rgba(0,0,0,0.1)' }, // Stripe style
  27: { background: '#2e7d32', borderRadius: '8px', boxShadow: '0 4px 14px rgba(46, 125, 50, 0.25)' }, // Vercel style
  28: { background: '#2e7d32', borderRadius: '10px', border: '1px solid rgba(255,255,255,0.1)' }, // Linear style
  29: { background: 'linear-gradient(135deg, #388e3c, #2e7d32)', borderRadius: '8px', boxShadow: '0 4px 12px rgba(46, 125, 50, 0.3)' }, // Modern SaaS
  30: { background: '#2e7d32', borderRadius: '12px', boxShadow: '0 0 0 1px rgba(255,255,255,0.1)' }, // Subtle ring

  // 31-35: E-commerce (Amazon, Shopify style)
  31: { background: 'linear-gradient(180deg, #43a047, #2e7d32)', borderRadius: '4px' }, // Amazon style
  32: { background: '#2e7d32', borderRadius: '4px', boxShadow: '0 1px 3px rgba(0,0,0,0.2)' }, // Shopify style
  33: { background: '#2e7d32', borderRadius: '6px', fontWeight: '700' }, // Bold CTA
  34: { background: 'linear-gradient(180deg, #4caf50 0%, #2e7d32 100%)', borderRadius: '8px', boxShadow: '0 2px 5px rgba(0,0,0,0.15)' }, // Premium e-commerce
  35: { background: '#2e7d32', borderRadius: '0' }, // Retangular (moda/luxo)

  // 36-40: Apps / Mobile (iOS, Android patterns)
  36: { background: '#2e7d32', borderRadius: '14px' }, // iOS style
  37: { background: '#2e7d32', borderRadius: '50px', padding: '0.85rem 2rem' }, // Pill grande (apps)
  38: { background: '#2e7d32', borderRadius: '8px', boxShadow: '0 2px 8px rgba(46, 125, 50, 0.4)' }, // Android Material
  39: { background: 'linear-gradient(135deg, #43a047, #2e7d32)', borderRadius: '50px' }, // Gradient pill
  40: { background: '#2e7d32', borderRadius: '16px', boxShadow: '0 4px 16px rgba(46, 125, 50, 0.3)' }, // Super rounded

  // 41-45: Premium / Luxury
  41: { background: 'linear-gradient(180deg, #4caf50 0%, #2e7d32 40%, #1b5e20 100%)' }, // 3 tons
  42: { background: '#2e7d32', boxShadow: '0 8px 24px rgba(46, 125, 50, 0.4), inset 0 1px 0 rgba(255,255,255,0.1)' }, // Glow premium
  43: { background: 'linear-gradient(135deg, #388e3c, #2e7d32)', border: '1px solid rgba(255,255,255,0.15)', boxShadow: '0 4px 16px rgba(46, 125, 50, 0.3)' }, // Full premium
  44: { background: '#2e7d32', letterSpacing: '0.05em', textTransform: 'uppercase', fontSize: '0.8rem' }, // Luxury uppercase
  45: { background: '#1b5e20', border: '1px solid #2e7d32', boxShadow: '0 4px 12px rgba(27, 94, 32, 0.4)' }, // Dark premium

  // 46-50: Especiais / Criativos
  46: { background: '#2e7d32', borderLeft: '4px solid #4caf50', borderRadius: '0 8px 8px 0' }, // Accent bar
  47: { background: '#2e7d32', boxShadow: '0 0 0 3px rgba(46, 125, 50, 0.3)' }, // Ring glow
  48: { background: 'linear-gradient(90deg, #1b5e20, #2e7d32, #388e3c, #2e7d32, #1b5e20)' }, // Symmetric gradient
  49: { background: '#2e7d32', borderBottom: '3px solid #1b5e20' }, // Underline accent
  50: { background: 'linear-gradient(135deg, #2e7d32, #1b5e20)', boxShadow: '0 6px 24px rgba(27, 94, 32, 0.45), inset 0 1px 0 rgba(255,255,255,0.15)', border: '1px solid rgba(76, 175, 80, 0.2)', borderRadius: '10px' }, // Ultimate
}

const buttonNames = {
  1: 'Flat Puro (mais usado)',
  2: 'Flat Arredondado (Google)',
  3: 'Flat + Sombra (Bootstrap)',
  4: 'Flat Quadrado (Corporativo)',
  5: 'Pill (Apps Modernos)',
  6: 'Material Elevation 1',
  7: 'Material Elevation 2',
  8: 'Material Elevation 3',
  9: 'Colored Shadow',
  10: 'Strong Colored Shadow',
  11: 'Gradiente Diagonal',
  12: 'Gradiente Vertical',
  13: 'Gradiente Horizontal',
  14: 'Gradiente Claro',
  15: 'Gradiente Escuro',
  16: 'Borda Sutil',
  17: 'Borda Escura',
  18: 'Borda Clara',
  19: 'Borda + Arredondado',
  20: 'Ghost/Outline',
  21: '3D Clássico',
  22: '3D Arredondado',
  23: 'Inset Bottom',
  24: 'Brilho Interno',
  25: '3D + Gradiente',
  26: 'Stripe Style',
  27: 'Vercel Style',
  28: 'Linear Style',
  29: 'Modern SaaS',
  30: 'Subtle Ring',
  31: 'Amazon Style',
  32: 'Shopify Style',
  33: 'Bold CTA',
  34: 'Premium E-commerce',
  35: 'Retangular (Luxo)',
  36: 'iOS Style',
  37: 'Pill Grande (Apps)',
  38: 'Android Material',
  39: 'Gradient Pill',
  40: 'Super Rounded',
  41: '3 Tons Premium',
  42: 'Glow Premium',
  43: 'Full Premium',
  44: 'Luxury Uppercase',
  45: 'Dark Premium',
  46: 'Accent Bar',
  47: 'Ring Glow',
  48: 'Symmetric Gradient',
  49: 'Underline Accent',
  50: 'Ultimate',
}

const baseButtonStyle = {
  display: 'inline-flex',
  alignItems: 'center',
  gap: '0.5rem',
  padding: '0.75rem 1.5rem',
  fontSize: '0.9rem',
  fontWeight: '600',
  border: 'none',
  borderRadius: '10px',
  cursor: 'pointer',
  transition: 'all 0.3s ease',
  color: '#fff',
  whiteSpace: 'nowrap',
}

export default function ButtonShowcase() {
  return (
    <div style={{
      minHeight: '100vh',
      background: 'linear-gradient(135deg, #0a0f0a 0%, #111a11 50%, #0d120d 100%)',
      padding: '2rem',
    }}>
      <div style={{ textAlign: 'center', marginBottom: '3rem' }}>
        <h1 style={{ fontSize: '2.5rem', fontWeight: '700', color: '#fff', marginBottom: '0.5rem' }}>
          Padrões de Mercado
        </h1>
        <p style={{ color: 'rgba(255, 255, 255, 0.6)', fontSize: '1.1rem' }}>
          50 estilos ordenados do mais usado ao mais específico
        </p>
      </div>

      <div style={{
        display: 'grid',
        gridTemplateColumns: 'repeat(auto-fill, minmax(300px, 1fr))',
        gap: '1.5rem',
        maxWidth: '1400px',
        margin: '0 auto',
      }}>
        {Array.from({ length: 50 }, (_, i) => i + 1).map(num => (
          <div key={num} style={{
            background: 'rgba(255, 255, 255, 0.03)',
            border: '1px solid rgba(255, 255, 255, 0.08)',
            borderRadius: '16px',
            padding: '1.5rem',
            display: 'flex',
            flexDirection: 'column',
            alignItems: 'center',
            gap: '1rem',
          }}>
            <span style={{ fontSize: '0.75rem', color: 'rgba(255, 255, 255, 0.4)', fontWeight: '600' }}>
              #{num}
            </span>
            <button style={{ ...baseButtonStyle, ...buttonStyles[num] }}>
              Começar Agora <ArrowRight size={16} />
            </button>
            <span style={{ fontSize: '0.85rem', color: 'rgba(255, 255, 255, 0.7)', fontWeight: '500', textAlign: 'center' }}>
              {buttonNames[num]}
            </span>
          </div>
        ))}
      </div>
    </div>
  )
}
