import type { DemoUser } from '../../../types/dashboard'

interface UserSelectorProps {
  users: DemoUser[]
  selected: string
  onChange: (userId: string) => void
}

export function UserSelector({ users, selected, onChange }: UserSelectorProps) {
  return (
    <select
      className="supplier-selector"
      value={selected}
      onChange={(e) => onChange(e.target.value)}
      aria-label="Select demo user"
    >
      {users.map((u) => (
        <option key={u.user_id} value={u.user_id}>
          {u.display_name}
        </option>
      ))}
    </select>
  )
}
