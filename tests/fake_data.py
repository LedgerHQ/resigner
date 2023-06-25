import time

from ..src.models import (
    Utxos,
    SpentUtxos,
    AggregateSpends,
    SignedSpends
)

def fake_data():
    """Insert test data for testing models """ 

    # Insert Utxos data
    Utxos.insert(
        40,
        time.time()-21200,
        "67d4fe1ef563778fcbed99602788bf645fa961e3211e677573e38aec11f1d19a",
        0,
        36867904    
    )

    # Insert SpentUtxos data
    SpentUtxos.insert(
        "67d4fe1ef563778fcbed99602788bf645fa961e3211e677573e38aec11f1d19a",
        0,
        1
    )

    # Insert AggregateSpends data
    AggregateSpends.insert(
        43454445,
        193038438,
        234378349
    )

    # Insert SignedSpends data
    SignedSpends.insert(
        unsigned_psbt="cHNidP8BAHECAAAAAbU5tQSXtwlf5ZamU+wwrLjHFp1p6WQh7haL/sLFYuxTAAAAA\
        AD/////AnhBDwAAAAAAFgAUzun4goil9JgBkaKNeuCP9YQFDad4QQ8AAAAAABYAFI2GH/borPHKKjs91ZyG8uigq6dcAAAAAAAAAAA=",
        signed_psbt="cHNidP8BAHECAAAAAbU5tQSXtwlf5ZamU+wwrLjHFp1p6WQh7haL/sLFYuxTAAAAAAD/////AnhBDwAAAAAAFgAUzun4goil9JgBkaKNeuC\
        P9YQFDad4QQ8AAAAAABYAFI2GH/borPHKKjs91ZyG8uigq6dcAAAAAAABAIcCAAAAAtu5pTheUzdsTaMCEPj3XKboMAyYzABmIIeOWMhbhTYlAA\
        AAAAD//////uSTLbibcqSd/Z9ieSBWJ2psv+9qvoGrzWEa60rCx9cAAAAAAP////8BuIMeAAAAAAAiACAiTLUDp/eDV5m5wi7gw8fZPQkDVuMOc\
        AFcPrv6UVowdAAAAAAAACICA0nMQzJPetlLtAepvxK8UK/Z57QwpHJXLxtjy1VQNPUqENPtiCUAAACAAAAAgAMAAIAA",
        destination="bcrt1q0qjqsqessarh39628z0y9pa5l2yga84xnsnj2v",
        amount_sats=21333455,
        utxo_id=1,
        request_timestamp=time.time()-3600

    )