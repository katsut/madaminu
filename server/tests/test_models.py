import uuid

from sqlalchemy import select

from madaminu.models import ConnectionStatus, Game, GameStatus, Player


async def test_create_game(db_session):
    game = Game(
        id=str(uuid.uuid4()),
        room_code="ABC123",
        status=GameStatus.waiting,
    )
    db_session.add(game)
    await db_session.commit()

    result = await db_session.execute(select(Game).where(Game.room_code == "ABC123"))
    saved_game = result.scalar_one()
    assert saved_game.room_code == "ABC123"
    assert saved_game.status == GameStatus.waiting


async def test_create_player(db_session):
    game = Game(
        id=str(uuid.uuid4()),
        room_code="XYZ789",
        status=GameStatus.waiting,
    )
    db_session.add(game)
    await db_session.flush()

    player = Player(
        id=str(uuid.uuid4()),
        game_id=game.id,
        session_token=str(uuid.uuid4()),
        display_name="Alice",
        is_host=True,
        connection_status=ConnectionStatus.online,
    )
    db_session.add(player)
    await db_session.commit()

    result = await db_session.execute(select(Player).where(Player.game_id == game.id))
    saved_player = result.scalar_one()
    assert saved_player.display_name == "Alice"
    assert saved_player.is_host is True
    assert saved_player.connection_status == ConnectionStatus.online
