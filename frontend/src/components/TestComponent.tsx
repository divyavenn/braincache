import { useState } from 'react'

export const TestComponent = () => {
  const [count, setCount] = useState(0)

  return (
    <div style={{ 
      padding: '20px', 
      margin: '20px', 
      border: '2px solid blue',
      borderRadius: '8px',
      textAlign: 'center' 
    }}>
      <h1>Test Component</h1>
      <p>Count: {count}</p>
      <button 
        onClick={() => setCount(count + 1)}
        style={{
          padding: '10px 20px',
          backgroundColor: '#0066cc',
          color: 'white',
          border: 'none',
          borderRadius: '4px',
          cursor: 'pointer'
        }}
      >
        Click me!
      </button>
    </div>
  )
}
