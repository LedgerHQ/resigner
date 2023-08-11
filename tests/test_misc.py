import pytest

from ..src.analysis import descriptor_analysis
from ..src import IncompatibleDescriptor

MIN_LOCKTIME_HEIGHT = 12960
MIN_LOCKTIME_SECS = 7776000

resigner_xpriv = "tprv8ZgxMBicQKsPd8HVrctDUh989C3ptBD7n35gZTrm2uW5y1Jzk2ZQx8ampcc91ksvg2Lin2xoh2H8RouhJxGvTzPySqUcW1ziTiy9vZQ6aQF/84'/1'/0'/0/*"
participant_1 = "[7d442e6e/84'/1'/0']tpubDDBDavw67bWnpL88ckZUADqDgj8puFRaDmfgYai9hh3dh6psC16epkERk8YLaZf71qQJs9FMVha44hSf95hACafU9wkpPBKSLYQioc1xaCW/0/*"
participant_2 = "[b2a87df5/84'/1'/0']tpubDDY1iXqzGkhm8Ex1ARE6RNsNw8f75n2QKaceQj6W4Da2GenCkHrnNes5m2C9quedLWN6FouFrGn8YBPnRhbxCs4gHLKs9SDkmP9sAzLNUuq/0/*"
participant_3 = "[dcef75e7/84'/1'/0']tpubDD93N1A9ymCm4aSi75HMqaqfWn4CNo1Wmxx46p6mrxi5jC36TNxntWBSFzwYrsBJTRek5qdgLEwkzpDstS2fhAtKJbhVvi44wNVVxGGbeNz/0/*"
participant_4 = "[72900321/84'/1'/0']tpubDCakBgmkbzzee1YsG4B483fputQyJ7NYkz9Np1d3ZwCZbJ744Lu7s4NzRnWdBAGTG3JLcTJLUB7oweHtJddgUAGAYV4jrc4Qjnt57YyQqU8/0/*"
recovery_key = "[af9599f9/84'/1'/0']tpubDCPpTnHp4m8vmACxvNYtrwmVk8iEG8P3zyG9oc9L63ACNDyBFMEdoQoG5yKGiRs5gzw6w3uDHmMdojMZBkmgsrmXk6suKCRCQP1wsY7JaUf/0/*"  # Recovery Key

DESCRIPTORS = [
    f"wsh(and_v(v:pk({participant_1}),or_d(pk({resigner_xpriv}),older(12960))))",
    f"wsh(and_v(v:pk({participant_2}),or_d(pk({resigner_xpriv}),older(8960))))",
    f"wsh(and_v(v:pk({participant_3}),or_d(pk({resigner_xpriv}),older(179600))))",
    f"wsh(andor(pk({participant_4}),pk({resigner_xpriv}),and_v(v:pk({recovery_key}),older(12960))))",
    f"wsh(and_v(or_c(pk({resigner_xpriv}),v:older(12960)),multi(2,{participant_1},{participant_2},{participant_3})))",
    f"wsh(and_v(or_c(pk({resigner_xpriv}),or_c(pk({recovery_key}),v:older(12990))),pk({participant_2})))"
]

#@pytest.mark.parameterize("desc", DESCRIPTORS)
def test_descriptors(config, bitcoind):

    # Single user
    config.set({"desc": DESCRIPTORS[0]}, "wallet")
    try:
        descriptor_analysis(config)
    except Exception as excinfo:
        pytest.fail(f"unexpected Exception raised: {excinfo}")

    # TimeLock test
    config.set({"desc": DESCRIPTORS[1]}, "wallet")
    with pytest.raises(IncompatibleDescriptor) as excinfo:
        descriptor_analysis(config)
    assert str(excinfo.value) == f"minimum locktime in blocks: {MIN_LOCKTIME_HEIGHT}. But was set to 8960"

    # Testing more complex miniscript
    config.set({"desc": DESCRIPTORS[3]}, "wallet")
    try:
        descriptor_analysis(config)
    except Exception as excinfo:
        pytest.fail(f"unexpected Exception raised: {excinfo}")

    config.set({"desc": DESCRIPTORS[3]}, "wallet")
    try:
        descriptor_analysis(config)
    except Exception as excinfo:
        pytest.fail(f"unexpected Exception raised: {excinfo}")

    config.set({"desc": DESCRIPTORS[3]}, "wallet")
    try:
        descriptor_analysis(config)
    except Exception as excinfo:
        pytest.fail(f"unexpected Exception raised: {excinfo}")