# P3-004: State очищается до commit в box_cancel

## Severity: P3 (Nice-to-have)

## Описание
В `box_cancel` FSM state очищается до того, как изменения сохранены в БД. Если commit упадёт, пользователь потеряет state, но заказ останется в старом статусе.

## Файл
`handlers/box.py` - функция `box_cancel`

## Проблемный паттерн
```python
await state.clear()  # State очищен

# ... код ...

await session.commit()  # Если упадёт здесь - state уже потерян
```

## Решение
Очищать state после успешного commit:

```python
async def box_cancel(callback: CallbackQuery, state: FSMContext):
    data = await state.get_data()
    order_id = data.get("order_id")

    if order_id:
        async with get_session() as session:
            result = await session.execute(
                select(BoxOrder).where(BoxOrder.id == order_id)
            )
            order = result.scalar_one_or_none()
            if order and order.status == BoxOrderStatus.PENDING:
                order.status = BoxOrderStatus.CANCELLED
                await session.commit()  # Сначала commit

    await state.clear()  # Потом clear
    await callback.message.edit_text(texts.BOX_LATER)
```

## Влияние
- Редкий edge case
- Улучшает надёжность при сбоях БД
