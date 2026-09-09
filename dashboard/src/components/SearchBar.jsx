/**
 * dashboard/src/components/SearchBar.jsx
 *
 * Debounced text input for filtering/highlighting graph nodes by
 * name, phone, or alias. Calls onSearch(value) after the user stops
 * typing for DEBOUNCE_MS, rather than on every keystroke.
 */

import { Search, X } from 'lucide-react'
import { useEffect, useRef, useState } from 'react'

const DEBOUNCE_MS = 250

export default function SearchBar({ onSearch }) {
  const [value, setValue] = useState('')
  const timerRef = useRef(null)

  useEffect(() => {
    clearTimeout(timerRef.current)
    timerRef.current = setTimeout(() => onSearch?.(value), DEBOUNCE_MS)
    return () => clearTimeout(timerRef.current)
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [value])

  return (
    <div className="search-bar">
      <span className="search-bar-icon">
        <Search size={15} />
      </span>
      <input
        type="text"
        value={value}
        onChange={(e) => setValue(e.target.value)}
        placeholder="Search by name, phone, or alias..."
        aria-label="Search entities"
      />
      {value && (
        <button type="button" className="search-clear" onClick={() => setValue('')} aria-label="Clear search">
          <X size={15} />
        </button>
      )}
    </div>
  )
}
