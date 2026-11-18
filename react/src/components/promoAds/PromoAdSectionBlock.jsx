import PromoAdSlotCarousel from './PromoAdSlotCarousel';

/**
 * Renderiza una sección completa de publicidad (1, 2, 3 o 4 columnas).
 * Agrupa los ítems por su propiedad `slot` (1..layout_type) manteniendo el orden.
 */
export default function PromoAdSectionBlock({ section }) {
  const layoutType = section.layout_type || 1;
  const slots = Array.from({ length: layoutType }, (_, i) => i + 1);

  const itemsBySlot = slots.reduce((acc, slotNum) => {
    acc[slotNum] = (section.items || [])
      .filter((item) => item.slot === slotNum)
      .sort((a, b) => (a.display_order ?? 0) - (b.display_order ?? 0));
    return acc;
  }, {});

  const hasAnyItem = slots.some((slotNum) => itemsBySlot[slotNum].length > 0);
  if (!hasAnyItem) {
    return null;
  }

  return (
    <section className="promo-ads__section" aria-label={section.title || 'Sección publicitaria'}>
      {section.title && (
        <header className="promo-ads__section-header">
          <h2 className="promo-ads__section-title">{section.title}</h2>
        </header>
      )}

      <div className={`promo-ads__grid promo-ads__grid--cols-${layoutType}`}>
        {slots.map((slotNum) => (
          <PromoAdSlotCarousel key={slotNum} items={itemsBySlot[slotNum]} />
        ))}
      </div>
    </section>
  );
}
