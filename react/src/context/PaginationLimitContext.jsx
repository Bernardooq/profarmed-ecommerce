import { createContext, useContext, useState } from 'react';

const PaginationLimitContext = createContext(null);

export const PaginationLimitProvider = ({ children }) => {
  const [limit, setLimit] = useState(() => {
    const saved = localStorage.getItem('customLimitSelection');
    return saved ? parseInt(saved, 10) : 100;
  });

  const changeLimit = (newLimit) => {
    const parsedLimit = parseInt(newLimit, 10);
    setLimit(parsedLimit);
    localStorage.setItem('customLimitSelection', parsedLimit.toString());
  };

  return (
    <PaginationLimitContext.Provider value={{ limit, changeLimit }}>
      {children}
    </PaginationLimitContext.Provider>
  );
};

export const usePaginationLimit = () => {
  const context = useContext(PaginationLimitContext);
  if (!context) {
    throw new Error('usePaginationLimit must be used within a PaginationLimitProvider');
  }
  return context;
};
