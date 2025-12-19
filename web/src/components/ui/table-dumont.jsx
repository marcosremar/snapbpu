/**
 * Table Components - Adaptado do TailAdmin para Dumont Cloud
 * Paleta: Dark theme com accent verde (#4ade80, #22c55e)
 */

// Table Component
export const Table = ({ children, className = "" }) => {
  return (
    <div className="overflow-x-auto rounded-xl border border-gray-800/50 bg-[#131713]">
      <table className={`min-w-full ${className}`}>
        {children}
      </table>
    </div>
  );
};

// TableHeader Component
export const TableHeader = ({ children, className = "" }) => {
  return (
    <thead className={`bg-[#1a1f1a] border-b border-gray-800/50 ${className}`}>
      {children}
    </thead>
  );
};

// TableBody Component
export const TableBody = ({ children, className = "" }) => {
  return (
    <tbody className={`divide-y divide-gray-800/30 ${className}`}>
      {children}
    </tbody>
  );
};

// TableRow Component
export const TableRow = ({ children, className = "", onClick, hoverable = true }) => {
  return (
    <tr
      className={`
        ${hoverable ? 'hover:bg-[#1a1f1a] transition-colors cursor-pointer' : ''}
        ${className}
      `}
      onClick={onClick}
    >
      {children}
    </tr>
  );
};

// TableCell Component (Header)
export const TableHead = ({ children, className = "", align = "left" }) => {
  const alignClasses = {
    left: "text-left",
    center: "text-center",
    right: "text-right",
  };

  return (
    <th className={`
      px-4 py-3 text-xs font-medium text-gray-400 uppercase tracking-wider
      ${alignClasses[align]}
      ${className}
    `}>
      {children}
    </th>
  );
};

// TableCell Component (Body)
export const TableCell = ({ children, className = "", align = "left" }) => {
  const alignClasses = {
    left: "text-left",
    center: "text-center",
    right: "text-right",
  };

  return (
    <td className={`
      px-4 py-3 text-sm text-gray-300
      ${alignClasses[align]}
      ${className}
    `}>
      {children}
    </td>
  );
};

// Simple Table for quick use
export const SimpleTable = ({ columns, data, onRowClick }) => {
  return (
    <Table>
      <TableHeader>
        <TableRow hoverable={false}>
          {columns.map((col, idx) => (
            <TableHead key={idx} align={col.align}>
              {col.header}
            </TableHead>
          ))}
        </TableRow>
      </TableHeader>
      <TableBody>
        {data.map((row, rowIdx) => (
          <TableRow key={rowIdx} onClick={() => onRowClick?.(row)}>
            {columns.map((col, colIdx) => (
              <TableCell key={colIdx} align={col.align}>
                {col.render ? col.render(row[col.accessor], row) : row[col.accessor]}
              </TableCell>
            ))}
          </TableRow>
        ))}
      </TableBody>
    </Table>
  );
};

// Table with empty state
export const TableWithEmpty = ({ columns, data, emptyMessage = "Nenhum dado encontrado", onRowClick }) => {
  if (!data || data.length === 0) {
    return (
      <div className="rounded-xl border border-gray-800/50 bg-[#131713] p-8 text-center">
        <p className="text-gray-500">{emptyMessage}</p>
      </div>
    );
  }

  return <SimpleTable columns={columns} data={data} onRowClick={onRowClick} />;
};

export default Table;
