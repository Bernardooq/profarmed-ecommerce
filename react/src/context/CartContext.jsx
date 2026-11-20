import { createContext, useContext, useState, useEffect } from 'react';
import { orderService } from '../services/orderService';
import { productService } from '../services/productService';
import { useAuth } from './AuthContext';

const CartContext = createContext(null);

export const CartProvider = ({ children }) => {
  const { isAuthenticated, user } = useAuth();
  const [items, setItems] = useState([]);
  const [loading, setLoading] = useState(false);

  // Cargar carrito exclusivamente para clientes (no para staff operativo/interno)
  useEffect(() => {
    if (isAuthenticated && user?.role === 'customer') {
      loadCart();
    } else {
      setItems([]);
    }
  }, [isAuthenticated, user]);

  const loadCart = async () => {
    try {
      setLoading(true);
      const cartData = await orderService.getCart();
      setItems(cartData);
    } catch (error) {
      console.error('Failed to load cart:', error);
    } finally {
      setLoading(false);
    }
  };

  const addToCart = async (productId, quantity = 1) => {
    if (!isAuthenticated) {
      throw new Error('Please login to add items to cart');
    }

    try {
      // Verificar si el producto ya está en el carrito para validar stock si ya existe localmente
      const existingItem = items.find(item => item.product?.product_id === productId);
      
      if (existingItem) {
        const currentQuantityInCart = existingItem.quantity || 0;
        const stockAvailable = existingItem.product?.stock_count || 0;

        if (currentQuantityInCart >= stockAvailable) {
          throw new Error(`Ya tienes el máximo disponible (${stockAvailable} unidades) de este producto en tu carrito`);
        }

        const newTotalQuantity = currentQuantityInCart + quantity;

        if (newTotalQuantity > stockAvailable) {
          const maxCanAdd = stockAvailable - currentQuantityInCart;
          await orderService.addToCart(productId, maxCanAdd);
          await loadCart();

          const warningMsg = `Se agregaron ${maxCanAdd} unidades (máximo disponible). Ya tenías ${currentQuantityInCart} en el carrito. Stock total: ${stockAvailable}`;
          console.warn(warningMsg);
          const warning = new Error(warningMsg);
          warning.isWarning = true;
          throw warning;
        }
      }

      // Agregar directamente mediante el backend de pedidos B2B (el backend valida stock y precio del cliente)
      await orderService.addToCart(productId, quantity);
      await loadCart();
    } catch (error) {
      if (!error.isWarning) {
        console.error('Failed to add to cart:', error);
      }
      throw error;
    }
  };

  const updateQuantity = async (cartId, quantity) => {
    try {
      await orderService.updateCartItem(cartId, quantity);
      // Recargar el carrito completo para mantener sincronización
      await loadCart();
    } catch (error) {
      console.error('Failed to update quantity:', error);
      throw error;
    }
  };

  const removeItem = async (cartId) => {
    try {
      await orderService.removeCartItem(cartId);
      // Recargar el carrito completo
      await loadCart();
    } catch (error) {
      console.error('Failed to remove item:', error);
      throw error;
    }
  };

  const clearCart = async () => {
    try {
      await orderService.clearCart();
      setItems([]);
    } catch (error) {
      console.error('Failed to clear cart:', error);
      throw error;
    }
  };

  const checkout = async (shippingAddressNumber = 1, orderNotes = '', invoiceType = 'factura') => {
    try {
      const order = await orderService.checkout(shippingAddressNumber, orderNotes, invoiceType);
      setItems([]);
      return order;
    } catch (error) {
      console.error('Checkout failed:', error);
      throw error;
    }
  };

  const importFromExcel = async (file) => {
    try {
      setLoading(true);
      const result = await orderService.importCartExcel(file);
      if (result.cart) {
        setItems(result.cart);
      } else {
        await loadCart();
      }
      return result;
    } catch (error) {
      console.error('Failed to import from Excel:', error);
      throw error;
    } finally {
      setLoading(false);
    }
  };

  // Computed values (itemCount = SKUs distintos cargados en el carrito)
  const itemCount = items.length;
  const totalPieces = items.reduce((sum, item) => sum + (item.quantity || 0), 0);
  const total = items.reduce((sum, item) => {
    const price = item.final_price ?? item.price_at_addition ?? item.product?.final_price ?? item.product?.base_price ?? item.product?.price ?? 0;
    const quantity = item.quantity || 0;
    return sum + (price * quantity);
  }, 0);

  const value = {
    items,
    loading,
    itemCount,
    total,
    addToCart,
    updateQuantity,
    removeItem,
    clearCart,
    checkout,
    importFromExcel,
    refreshCart: loadCart
  };

  return <CartContext.Provider value={value}>{children}</CartContext.Provider>;
};

export const useCart = () => {
  const context = useContext(CartContext);
  if (!context) {
    throw new Error('useCart must be used within CartProvider');
  }
  return context;
};