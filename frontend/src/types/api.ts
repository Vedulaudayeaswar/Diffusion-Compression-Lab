export type JobStatus = 'queued' | 'running' | 'completed' | 'error'

export interface Metrics {
  original_file_size: number
  compressed_file_size: number
  payload_size?: number
  header_size?: number
  bpp: number
  compression_ratio: number
  mse?: number | null
  psnr: number | null
  ssim: number | null
  encode_time_seconds?: number | null
  decode_time_seconds?: number | null
  latent_shape?: number[] | null
  diffusion_timestep?: number | null
  diffusion_steps?: number | null
}

export interface Job {
  id: string
  status: JobStatus
  progress: number
  stage: string
  created_at: string
  started_at: string | null
  completed_at: string | null
  metrics: Metrics | null
  output: { dfc2_url: string; reconstruction_url: string; metadata: Record<string, unknown> } | null
  error: string | null
}

export interface ModelStatus {
  model_id: string
  vae_loaded: boolean
  unet_loaded: boolean
  codec_loaded: boolean
  scheduler_loaded?: boolean
  device: string
  dtype: string
  checkpoint: string
  checkpoint_size: number | null
  status: string
  error: string | null
}

export interface Dfc2Metadata {
  channels: number
  image_height: number
  image_width: number
  latent_height: number
  latent_width: number
  timestep_normalized: number
  payload_byte_length: number
  payload_bit_length: number
  [key: string]: unknown
}
