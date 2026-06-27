import type { SupplierInfo } from '../../../types/dashboard'

interface SupplierSelectorProps {
  suppliers: SupplierInfo[]
  selected: string
  onChange: (code: string) => void
}

export function SupplierSelector({
  suppliers,
  selected,
  onChange,
}: SupplierSelectorProps) {
  return (
    <select
      className="supplier-selector"
      value={selected}
      onChange={(e) => onChange(e.target.value)}
      aria-label="Select supplier"
    >
      {suppliers.map((s) => (
        <option key={s.supplier_code} value={s.supplier_code}>
          {s.supplier_name}
        </option>
      ))}
    </select>
  )
}
