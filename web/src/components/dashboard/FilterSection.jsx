import React, { useState } from 'react';
import { ChevronDown } from 'lucide-react';
import { Card, CardContent } from '../tailadmin-ui';

// Collapsible Filter Section
const FilterSection = ({ title, icon: Icon, children, defaultOpen = true }) => {
  const [isOpen, setIsOpen] = useState(defaultOpen);

  return (
    <Card className="overflow-hidden hover:border-gray-300 dark:hover:border-dark-surface-hover transition-all">
      <button
        onClick={() => setIsOpen(!isOpen)}
        className="w-full flex items-center justify-between p-3.5 text-left hover:bg-gray-50 dark:hover:bg-dark-surface-hover transition-colors group"
      >
        <div className="flex items-center gap-3">
          <div className="p-1.5 rounded-md bg-gray-100 dark:bg-dark-surface-secondary group-hover:bg-gray-200 dark:group-hover:bg-dark-surface-hover transition-colors">
            <Icon className="w-4 h-4 text-gray-500 dark:text-gray-400" />
          </div>
          <span className="text-sm font-medium text-gray-900 dark:text-gray-200">{title}</span>
        </div>
        <ChevronDown className={`w-4 h-4 text-gray-500 transition-all ${isOpen ? 'rotate-180' : ''}`} />
      </button>
      <div className={`overflow-hidden transition-all duration-300 ease-in-out ${isOpen ? 'max-h-[2000px] opacity-100' : 'max-h-0 opacity-0'}`}>
        <CardContent className="pt-2 border-t border-gray-100 dark:border-gray-700/30 animate-slideIn">
          {children}
        </CardContent>
      </div>
    </Card>
  );
};

export default FilterSection;
