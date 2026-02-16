import type { Theme } from '../api';

interface ThemeCardProps {
  theme: Theme;
  index: number;
}

const COLORS = [
  '#4f46e5', // indigo
  '#0891b2', // cyan
  '#059669', // emerald
  '#d97706', // amber
  '#dc2626', // red
  '#7c3aed', // violet
];

export default function ThemeCard({ theme, index }: ThemeCardProps) {
  const color = COLORS[index % COLORS.length];

  return (
    <div className="theme-card" style={{ borderLeftColor: color }}>
      <div className="theme-header">
        <span className="theme-number" style={{ backgroundColor: color }}>
          {index + 1}
        </span>
        <h3 className="theme-title">{theme.title}</h3>
      </div>
      <p className="theme-description">{theme.description}</p>
      {theme.student_names.length > 0 && (
        <div className="theme-students">
          {theme.student_names.map((name, i) => (
            <span key={i} className="student-tag" style={{ borderColor: color, color }}>
              {name}
            </span>
          ))}
        </div>
      )}
    </div>
  );
}
