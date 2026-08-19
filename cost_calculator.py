"""
Moduł kalkulacji kosztów API OpenAI
Ceny aktualne na grudzień 2025
"""
import logging

logger = logging.getLogger(__name__)


class CostCalculator:
    """Kalkulator kosztów dla OpenAI API"""

    # Ceny OpenAI API (grudzień 2025)
    # Źródło: https://platform.openai.com/docs/pricing

    # Whisper - transkrypcja audio
    WHISPER_PER_MINUTE_USD = 0.006  # $0.006 za minutę

    # ⚠️ DO POTWIERDZENIA NA CENNIKU OPENAI ⚠️
    # gpt-4o-transcribe-diarize rozlicza się za tokeny, nie za minuty, ale do
    # szacunku używamy przelicznika minutowego. Wartość poniżej to ROBOCZE
    # założenie równe stawce Whispera — dopóki nie zostanie zweryfikowana,
    # koszty transkrypcji w statystykach mogą być zaniżone lub zawyżone.
    # Rzeczywiste zużycie tokenów jest logowane przy każdej transkrypcji.
    DIARIZE_PER_MINUTE_USD = 0.006

    # AssemblyAI Universal-2 ($0.15/godz.) + diaryzacja ($0.02/godz.).
    # Stawki z cennika, potwierdzone pomiarem: 171 s nagrania = $0.0081.
    ASSEMBLYAI_PER_HOUR_USD = 0.17

    # GPT-4o-mini - chat completion
    GPT4O_MINI_INPUT_PER_1M_TOKENS_USD = 0.15   # $0.15 za 1M tokenów input
    GPT4O_MINI_OUTPUT_PER_1M_TOKENS_USD = 0.60  # $0.60 za 1M tokenów output

    # Text-Embedding-3-Small - embeddings
    EMBEDDING_SMALL_PER_1M_TOKENS_USD = 0.02    # $0.02 za 1M tokenów

    @staticmethod
    def calculate_whisper_cost(duration_seconds):
        """
        Oblicza koszt transkrypcji Whisper

        Args:
            duration_seconds: Długość audio w sekundach

        Returns:
            float: Koszt w USD
        """
        if duration_seconds is None or duration_seconds <= 0:
            return 0.0

        duration_minutes = duration_seconds / 60.0
        cost = duration_minutes * CostCalculator.WHISPER_PER_MINUTE_USD

        logger.debug(f"Whisper cost: {duration_seconds}s = {duration_minutes:.2f}min = ${cost:.6f}")
        return round(cost, 6)

    @staticmethod
    def calculate_transcription_cost(duration_seconds, model=None):
        """
        Koszt transkrypcji. Dla modelu diaryzującego używa DIARIZE_PER_MINUTE_USD,
        w pozostałych przypadkach stawki Whispera.
        """
        if model == "assemblyai":
            koszt = (duration_seconds / 3600.0) * CostCalculator.ASSEMBLYAI_PER_HOUR_USD
        else:
            stawka = (CostCalculator.DIARIZE_PER_MINUTE_USD
                      if model and "diarize" in model
                      else CostCalculator.WHISPER_PER_MINUTE_USD)
            koszt = (duration_seconds / 60.0) * stawka
        logger.info(f"Koszt transkrypcji ({model or 'whisper'}): "
                    f"{duration_seconds}s = ${koszt:.6f}")
        return koszt

    @staticmethod
    def calculate_gpt_cost(input_tokens, output_tokens):
        """
        Oblicza koszt GPT-4o-mini

        Args:
            input_tokens: Liczba tokenów wejściowych
            output_tokens: Liczba tokenów wyjściowych

        Returns:
            tuple: (cost_input_usd, cost_output_usd, cost_total_usd)
        """
        if input_tokens is None:
            input_tokens = 0
        if output_tokens is None:
            output_tokens = 0

        cost_input = (input_tokens / 1_000_000) * CostCalculator.GPT4O_MINI_INPUT_PER_1M_TOKENS_USD
        cost_output = (output_tokens / 1_000_000) * CostCalculator.GPT4O_MINI_OUTPUT_PER_1M_TOKENS_USD
        cost_total = cost_input + cost_output

        logger.debug(f"GPT cost: {input_tokens} input + {output_tokens} output = ${cost_total:.6f}")
        return (round(cost_input, 6), round(cost_output, 6), round(cost_total, 6))

    @staticmethod
    def calculate_embedding_cost(tokens):
        """
        Oblicza koszt text-embedding-3-small

        Args:
            tokens: Liczba tokenów

        Returns:
            float: Koszt w USD
        """
        if tokens is None or tokens <= 0:
            return 0.0

        cost = (tokens / 1_000_000) * CostCalculator.EMBEDDING_SMALL_PER_1M_TOKENS_USD

        logger.debug(f"Embedding cost: {tokens} tokens = ${cost:.6f}")
        return round(cost, 6)

    @staticmethod
    def calculate_total_cost(whisper_cost, gpt_input_cost, gpt_output_cost, embedding_cost):
        """
        Oblicza łączny koszt przetworzenia notatki

        Args:
            whisper_cost: Koszt Whisper w USD
            gpt_input_cost: Koszt GPT input w USD
            gpt_output_cost: Koszt GPT output w USD
            embedding_cost: Koszt embedding w USD

        Returns:
            float: Łączny koszt w USD
        """
        costs = [whisper_cost or 0, gpt_input_cost or 0, gpt_output_cost or 0, embedding_cost or 0]
        total = sum(costs)

        logger.info(f"Total cost: Whisper ${whisper_cost:.6f} + GPT ${(gpt_input_cost or 0) + (gpt_output_cost or 0):.6f} + Embedding ${embedding_cost:.6f} = ${total:.6f}")
        return round(total, 6)

    @staticmethod
    def format_cost_usd(cost_usd):
        """
        Formatuje koszt do wyświetlenia

        Args:
            cost_usd: Koszt w USD

        Returns:
            str: Sformatowany koszt (np. "$0.0025" lub "$0.25")
        """
        if cost_usd is None or cost_usd == 0:
            return "$0.00"

        if cost_usd < 0.01:
            # Dla bardzo małych kosztów pokaż więcej miejsc po przecinku
            return f"${cost_usd:.4f}"
        else:
            return f"${cost_usd:.2f}"


# Przykładowe użycie
if __name__ == "__main__":
    logging.basicConfig(level=logging.DEBUG)

    # Przykład: 30-sekundowa notatka głosowa
    duration = 30  # sekund
    input_tokens = 150  # ~100 słów transkrypcji
    output_tokens = 80  # JSON z tematem, opisem, zadaniami
    embedding_tokens = 150  # Embedding dla tematu+opisu

    whisper = CostCalculator.calculate_whisper_cost(duration)
    gpt_in, gpt_out, gpt_total = CostCalculator.calculate_gpt_cost(input_tokens, output_tokens)
    embedding = CostCalculator.calculate_embedding_cost(embedding_tokens)
    total = CostCalculator.calculate_total_cost(whisper, gpt_in, gpt_out, embedding)

    print("\n📊 Przykład kalkulacji kosztów:")
    print(f"Audio: {duration}s")
    print(f"Whisper: {CostCalculator.format_cost_usd(whisper)}")
    print(f"GPT-4o-mini input ({input_tokens} tokens): {CostCalculator.format_cost_usd(gpt_in)}")
    print(f"GPT-4o-mini output ({output_tokens} tokens): {CostCalculator.format_cost_usd(gpt_out)}")
    print(f"Embedding ({embedding_tokens} tokens): {CostCalculator.format_cost_usd(embedding)}")
    print(f"━━━━━━━━━━━━━━━━━━━━━━━━━━━━")
    print(f"TOTAL: {CostCalculator.format_cost_usd(total)}")
