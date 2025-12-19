/**
 * Dumont UI - Design System
 * Componentes adaptados do TailAdmin para Dumont Cloud
 *
 * Paleta de cores:
 * - Background: #0e110e, #131713, #1a1f1a
 * - Accent Green: #4ade80, #22c55e
 * - Status: green (online), gray (offline), yellow (warning), red (error)
 *
 * Baseado em: TailAdmin (https://tailadmin.com)
 */

// Badge Components
export { default as Badge, StatusBadge, TrendBadge } from './badge-dumont';

// Alert Components
export { default as Alert, AlertInline, ToastAlert } from './alert-dumont';

// Table Components
export {
  Table,
  TableHeader,
  TableBody,
  TableRow,
  TableHead,
  TableCell,
  SimpleTable,
  TableWithEmpty,
} from './table-dumont';

// Modal Components
export {
  Modal,
  ModalHeader,
  ModalBody,
  ModalFooter,
  ConfirmModal,
} from './modal-dumont';

// Metric Components
export {
  MetricCard,
  MetricsGrid,
  MiniMetric,
} from './metric-card';

// New UI Components
export { Progress } from './progress';
export { Avatar, AvatarImage, AvatarFallback } from './avatar';
export { Popover, PopoverTrigger, PopoverAnchor, PopoverContent } from './popover';

// Re-export existing Shadcn components
export { Button } from './button';
export { Input } from './input';
export { Label } from './label';
export { Card, CardContent, CardHeader, CardTitle } from './card';
export { Tabs, TabsList, TabsTrigger } from './tabs';
export { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from './select';
export { Switch } from './switch';
export { Checkbox } from './checkbox';
export { Slider } from './slider';
