import { useCallback, useEffect, useRef, useState } from 'react'

function getRecognitionCtor() {
  if (typeof window === 'undefined') return null
  return window.SpeechRecognition || window.webkitSpeechRecognition || null
}

/**
 * Browser speech-to-text with pause detection (gaps between final phrases).
 */
export function useSpeechRecognition() {
  const [supported, setSupported] = useState(false)
  const [listening, setListening] = useState(false)
  const [transcript, setTranscript] = useState('')
  const [pauseCount, setPauseCount] = useState(0)
  const [durationSec, setDurationSec] = useState(0)

  const recognitionRef = useRef(null)
  const startTimeRef = useRef(0)
  const lastFinalRef = useRef(0)
  const pauseCountRef = useRef(0)
  const transcriptRef = useRef('')

  useEffect(() => {
    setSupported(!!getRecognitionCtor())
  }, [])

  const stop = useCallback(() => {
    const rec = recognitionRef.current
    if (rec) {
      try {
        rec.stop()
      } catch {
        /* ignore */
      }
    }
    recognitionRef.current = null
    setListening(false)
    if (startTimeRef.current) {
      setDurationSec(Math.round((Date.now() - startTimeRef.current) / 100) / 10)
    }
    setPauseCount(pauseCountRef.current)
  }, [])

  const start = useCallback(() => {
    const Ctor = getRecognitionCtor()
    if (!Ctor) {
      throw new Error(
        'Speech recognition is not supported in this browser. Use Chrome or Edge, or type your answer.',
      )
    }

    stop()

    const rec = new Ctor()
    rec.continuous = true
    rec.interimResults = true
    rec.lang = 'en-US'

    pauseCountRef.current = 0
    transcriptRef.current = ''
    startTimeRef.current = Date.now()
    lastFinalRef.current = Date.now()

    rec.onresult = (event) => {
      let interim = ''
      let finalChunk = ''
      for (let i = event.resultIndex; i < event.results.length; i += 1) {
        const piece = event.results[i][0].transcript
        if (event.results[i].isFinal) {
          finalChunk += piece
        } else {
          interim += piece
        }
      }
      if (finalChunk) {
        const now = Date.now()
        const gapSec = (now - lastFinalRef.current) / 1000
        if (lastFinalRef.current && gapSec >= 1.2) {
          pauseCountRef.current += 1
        }
        lastFinalRef.current = now
        const sep = transcriptRef.current && !transcriptRef.current.endsWith(' ') ? ' ' : ''
        transcriptRef.current = `${transcriptRef.current}${sep}${finalChunk.trim()}`
        setTranscript(transcriptRef.current)
        setPauseCount(pauseCountRef.current)
      } else if (interim) {
        const base = transcriptRef.current
        const sep = base && !base.endsWith(' ') ? ' ' : ''
        setTranscript(`${base}${sep}${interim}`.trim())
      }
    }

    rec.onerror = (event) => {
      if (event.error === 'not-allowed') {
        setListening(false)
        throw new Error('Microphone permission denied. Allow mic access in browser settings.')
      }
      if (event.error !== 'aborted' && event.error !== 'no-speech') {
        console.warn('Speech recognition error:', event.error)
      }
    }

    rec.onend = () => {
      if (recognitionRef.current === rec) {
        setListening(false)
        setDurationSec(Math.round((Date.now() - startTimeRef.current) / 100) / 10)
        setPauseCount(pauseCountRef.current)
      }
    }

    recognitionRef.current = rec
    rec.start()
    setListening(true)
    setTranscript('')
    setDurationSec(0)
    setPauseCount(0)
  }, [stop])

  const reset = useCallback(() => {
    stop()
    transcriptRef.current = ''
    setTranscript('')
    setPauseCount(0)
    setDurationSec(0)
    pauseCountRef.current = 0
  }, [stop])

  const getMetrics = useCallback(
    (mode = 'voice') => ({
      answer_mode: mode,
      duration_sec: durationSec || (startTimeRef.current ? (Date.now() - startTimeRef.current) / 1000 : 0),
      pause_count: pauseCountRef.current,
    }),
    [durationSec],
  )

  useEffect(() => () => stop(), [stop])

  return {
    supported,
    listening,
    transcript,
    pauseCount,
    durationSec,
    start,
    stop,
    reset,
    getMetrics,
    setTranscript,
  }
}
