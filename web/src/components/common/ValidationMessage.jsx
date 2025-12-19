import { AlertInline } from '../ui/dumont-ui'

/**
 * ValidationMessage - Consolidated validation display component
 * Handles displaying validation feedback consistently across the application
 * Wraps Dumont UI AlertInline for standardized validation messaging
 */
export const ValidationMessage = ({ validation, field, fullMessage = false }) => {
  if (!validation) return null

  const message = fullMessage
    ? validation.message
    : validation.message || `${field} inválido`

  return (
    <AlertInline variant={validation.valid ? 'success' : 'error'}>
      {message}
    </AlertInline>
  )
}

export default ValidationMessage
