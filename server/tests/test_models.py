import uuid

from sqlalchemy import select

from madaminu.models import ConnectionStatus, Game, GameStatus, Player


async def test_create_game(test_session):
    game = Game(
        id=str(uuid.uuid4()),
        room_code="ABC123",
        status=GameStatus.waiting,
    )
    test_session.add(game)
    await test_session.commit()

    result = await test_session.execute(select(Game).where(Game.room_code == "ABC123"))
    saved_game = result.scalar_one()
    assert saved_game.room_code == "ABC123"
    assert saved_game.status == GameStatus.waiting


async def test_create_player(test_session):
    game = Game(
        id=str(uuid.uuid4()),
        room_code="XYZ789",
        status=GameStatus.waiting,
    )
    test_session.add(game)
    await test_session.flush()

    player = Player(
        id=str(uuid.uuid4()),
        game_id=game.id,
        session_token=str(uuid.uuid4()),
        display_name="Alice",
        is_host=True,
        connection_status=ConnectionStatus.online,
    )
    test_session.add(player)
    await test_session.commit()

    result = await test_session.execute(select(Player).where(Player.game_id == game.id))
    saved_player = result.scalar_one()
    assert saved_player.display_name == "Alice"
    assert saved_player.is_host is True
    assert saved_player.connection_status == ConnectionStatus.online
